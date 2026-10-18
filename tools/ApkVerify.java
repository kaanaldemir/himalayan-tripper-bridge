import com.android.apksig.ApkVerifier;
import java.io.File;
import java.security.MessageDigest;
import java.util.HexFormat;
/** Verifies cryptographic integrity, not publisher identity against an external trust anchor. */
class ApkVerify {
  public static void main(String[] args) throws Exception {
    if (args.length == 0) throw new IllegalArgumentException("Supply at least one APK");
    boolean verified = true;
    for (String path : args) {
      var r = new ApkVerifier.Builder(new File(path)).build().verify();
      verified &= r.isVerified();
      System.out.println(new File(path).getName()+" verified="+r.isVerified()+" v2="+r.isVerifiedUsingV2Scheme()+" v3="+r.isVerifiedUsingV3Scheme()+" errors="+r.getErrors());
      for (var c : r.getSignerCertificates()) {
        System.out.println("certificate_sha256="+HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(c.getEncoded())));
        System.out.println("certificate_subject="+c.getSubjectX500Principal());
      }
    }
    if (!verified) throw new IllegalStateException("One or more APK signatures failed verification");
  }
}
