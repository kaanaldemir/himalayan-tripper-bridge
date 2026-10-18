import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.Arrays;
import javax.crypto.Cipher;

/** Synthetic test of the observed SSID || 32-byte session-key RSA payload.
 * No real bike key is used or written, and no authentication is bypassed.
 */
class DashAuthProbe {
  public static void main(String[] args) throws Exception {
    var generator = KeyPairGenerator.getInstance("RSA");
    generator.initialize(1024);
    var peer = generator.generateKeyPair();
    byte[] ssid = "RE_SYNTHETIC".getBytes(StandardCharsets.UTF_8);
    byte[] key = new byte[32];
    new SecureRandom().nextBytes(key);
    byte[] plain = new byte[ssid.length + key.length];
    System.arraycopy(ssid, 0, plain, 0, ssid.length);
    System.arraycopy(key, 0, plain, ssid.length, key.length);
    var rsa = Cipher.getInstance("RSA/ECB/PKCS1Padding");
    rsa.init(Cipher.ENCRYPT_MODE, peer.getPublic());
    byte[] ciphertext = rsa.doFinal(plain);
    if (ciphertext.length != 128) throw new AssertionError("Expected 128-byte ciphertext");
    rsa.init(Cipher.DECRYPT_MODE, peer.getPrivate());
    if (!Arrays.equals(rsa.doFinal(ciphertext), plain)) throw new AssertionError("Payload differs");
    Arrays.fill(key, (byte) 0);
    Arrays.fill(plain, (byte) 0);
    System.out.println("Synthetic RSA payload roundtrip passed: UTF-8 SSID + 32 session bytes, 128 ciphertext bytes; no real device tested.");
  }
}
