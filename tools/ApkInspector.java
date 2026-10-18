import jadx.api.*;
import java.io.*;
import java.nio.file.*;
/** Targeted static inspection. No APK code is executed. Requires the pinned JADX engine. */
class ApkInspector {
  public static void main(String[] args) throws Exception {
    if (args.length < 3) throw new IllegalArgumentException("Usage: ApkInspector APK OUTPUT_DIR CLASS... | @manifest | @smali:CLASS");
    var config = new JadxArgs();
    config.setInputFile(new File(args[0]));
    config.setSkipResources(true);
    config.setThreadsCount(2);
    config.setDeobfuscationOn(false);
    try (var jadx = new JadxDecompiler(config)) {
      jadx.load();
      // Create JavaClass wrappers from raw nodes. Avoid getInnerClasses() traversal,
      // which materializes code across the entire APK on this JADX version.
      jadx.getClassesWithInners();
      Path output = Path.of(args[1]);
      Files.createDirectories(output);
      for (int i=2;i<args.length;i++) {
        String name=args[i];
        if (name.equals("@manifest")) {
          for (var resource:jadx.getResources()) {
            if(resource.getOriginalName().endsWith("AndroidManifest.xml")) {
              Files.writeString(output.resolve("AndroidManifest.xml"),resource.loadContent().getText().getCodeStr());
              System.out.println("manifest decoded");
            }
          }
          continue;
        }
        boolean smali = name.startsWith("@smali:");
        if (smali) name=name.substring(7);
        if (!name.matches("[A-Za-z0-9_.$]+")) throw new IllegalArgumentException("Invalid class name");
        var node=jadx.searchClassNodeByOrigFullName(name);
        if(node==null) throw new IllegalArgumentException("Class not present in this APK: "+name);
        var source=smali ? node.getJavaNode().getSmali() : node.decompile().getCodeStr();
        if (source.isBlank()) throw new IllegalStateException("No source emitted for "+name+"; inspect its enclosing class or use @smali:");
        Files.writeString(output.resolve(name+(smali ? ".smali" : ".java")),source);
        System.out.println(name+" chars="+source.length());
      }
    }
  }
}
