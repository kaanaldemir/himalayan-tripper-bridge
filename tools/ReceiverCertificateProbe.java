import java.io.*;
import java.nio.file.*;
import java.security.*;
import java.security.cert.*;
import java.util.HexFormat;
import javax.net.ssl.*;

/** Check a public receiver certificate against a supplied public trust anchor.
 * No keys, APK execution, TLS session, or Android trust-provider equivalence.
 */
class ReceiverCertificateProbe {
  static X509Certificate read(String path) throws Exception {
    try (var input = Files.newInputStream(Path.of(path))) {
      return (X509Certificate) CertificateFactory.getInstance("X.509").generateCertificate(input);
    }
  }

  public static void main(String[] args) throws Exception {
    if (args.length != 2) throw new IllegalArgumentException("Usage: ReceiverCertificateProbe PUBLIC_CA_PEM PUBLIC_RECEIVER_CERT");
    var root = read(args[0]);
    var leaf = read(args[1]);
    leaf.checkValidity();
    leaf.verify(root.getPublicKey());
    var store = KeyStore.getInstance(KeyStore.getDefaultType());
    store.load(null, null);
    store.setCertificateEntry("supplied-public-anchor", root);
    var factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
    factory.init(store);
    boolean checked = false;
    for (var manager : factory.getTrustManagers()) {
      if (manager instanceof X509TrustManager trust) {
        trust.checkClientTrusted(new X509Certificate[]{leaf}, leaf.getPublicKey().getAlgorithm());
        checked = true;
      }
    }
    if (!checked) throw new IllegalStateException("No X509 trust manager");
    var sha = MessageDigest.getInstance("SHA-256");
    System.out.println("Public receiver certificate signature and JDK client trust passed; no TLS or Android execution.");
    System.out.println("anchor_sha256=" + HexFormat.of().formatHex(sha.digest(root.getEncoded())));
    System.out.println("receiver_sha256=" + HexFormat.of().formatHex(sha.digest(leaf.getEncoded())));
    System.out.println("receiver_not_after=" + leaf.getNotAfter().toInstant());
  }
}
