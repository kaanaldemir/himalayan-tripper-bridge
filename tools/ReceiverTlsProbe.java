import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.io.*;
import java.security.*;
import java.security.cert.*;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.*;
import java.util.concurrent.*;
import javax.net.ssl.*;

/** Loopback exercise of WPP's reversed TCP/TLS roles, using supplied public
 * receiver material and an independently generated synthetic server identity.
 * No Android Auto process, WPP messages, APK keys, or motorcycle are involved.
 */
class ReceiverTlsProbe {
  static X509Certificate certificate(String path) throws Exception {
    try (var input = Files.newInputStream(Path.of(path))) {
      return (X509Certificate) CertificateFactory.getInstance("X.509").generateCertificate(input);
    }
  }

  static X509TrustManager trust(X509Certificate root) throws Exception {
    var store = KeyStore.getInstance(KeyStore.getDefaultType());
    store.load(null, null);
    store.setCertificateEntry("anchor", root);
    var factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
    factory.init(store);
    for (var manager : factory.getTrustManagers()) {
      if (manager instanceof X509TrustManager result) return result;
    }
    throw new IllegalStateException("No X509 trust manager");
  }

  static SSLContext context(KeyStore keys, char[] password, X509TrustManager trust) throws Exception {
    var factory = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
    factory.init(keys, password);
    var context = SSLContext.getInstance("TLSv1.2");
    context.init(factory.getKeyManagers(), new TrustManager[]{trust}, new SecureRandom());
    return context;
  }

  static SSLSocket wrap(SSLContext context, Socket socket, boolean client) throws Exception {
    var tls = (SSLSocket) context.getSocketFactory().createSocket(socket, "127.0.0.1", socket.getPort(), true);
    tls.setUseClientMode(client);
    tls.setEnabledProtocols(new String[]{"TLSv1.2"});
    tls.setSoTimeout(5000);
    if (!client) tls.setNeedClientAuth(true);
    return tls;
  }

  public static void main(String[] args) throws Exception {
    if (args.length != 4) throw new IllegalArgumentException("Usage: ReceiverTlsProbe PUBLIC_CA PUBLIC_RECEIVER_CERT RECEIVER_PKCS8_PEM SYNTHETIC_SERVER_P12");
    // The password is for the disposable test keystore, never an account or device.
    char[] password = System.getenv().getOrDefault("SYNTHETIC_TLS_STORE_PASSWORD", "disposable-test-only").toCharArray();
    var serverKeys = KeyStore.getInstance("PKCS12");
    try (var input = Files.newInputStream(Path.of(args[3]))) { serverKeys.load(input, password); }
    var serverCert = (X509Certificate) serverKeys.getCertificate("synthetic-server");
    var anchor = certificate(args[0]);
    var receiverCert = certificate(args[1]);
    receiverCert.checkValidity();
    receiverCert.verify(anchor.getPublicKey());
    String pem = Files.readString(Path.of(args[2]))
        .replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "").replaceAll("\\s", "");
    var key = KeyFactory.getInstance("RSA").generatePrivate(new PKCS8EncodedKeySpec(Base64.getDecoder().decode(pem)));
    var receiverKeys = KeyStore.getInstance("PKCS12");
    receiverKeys.load(null, null);
    receiverKeys.setKeyEntry("receiver", key, password, new java.security.cert.Certificate[]{receiverCert, anchor});
    var phoneContext = context(serverKeys, password, trust(anchor));
    var receiverContext = context(receiverKeys, password, trust(serverCert));
    byte[] message = "synthetic transport bytes, not WPP".getBytes(StandardCharsets.US_ASCII);
    var executor = Executors.newSingleThreadExecutor();
    try (var listener = new ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"))) {
      listener.setSoTimeout(5000);
      var receiver = executor.submit(() -> {
        try (var raw = listener.accept(); var tls = wrap(receiverContext, raw, true)) {
          tls.startHandshake();
          tls.getOutputStream().write(message);
          if (!Arrays.equals(message, tls.getInputStream().readNBytes(message.length)))
            throw new AssertionError("Echo differs");
          return tls.getSession().getProtocol();
        }
      });
      try (var raw = new Socket()) {
        raw.connect(new InetSocketAddress("127.0.0.1", listener.getLocalPort()), 5000);
        try (var tls = wrap(phoneContext, raw, false)) {
          tls.startHandshake();
          var authenticated = (X509Certificate) tls.getSession().getPeerCertificates()[0];
          if (!authenticated.equals(receiverCert)) throw new AssertionError("Unexpected peer certificate");
          byte[] data = tls.getInputStream().readNBytes(message.length);
          if (!Arrays.equals(message, data)) throw new AssertionError("Payload differs");
          tls.getOutputStream().write(data);
          System.out.println("TLS loopback passed: TCP dialer = TLS server; accepting receiver = TLS client; client certificate required and verified.");
        }
      }
      System.out.println("protocol=" + receiver.get(10, TimeUnit.SECONDS));
      System.out.println("Scope: synthetic desktop TLS peers only; no Android Auto/WPP/AAP execution.");
    } finally {
      executor.shutdownNow();
      Arrays.fill(password, '\0');
    }
  }
}
