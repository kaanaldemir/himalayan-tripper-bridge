import jadx.api.*;
import java.io.*;
import java.nio.file.*;
import jadx.api.plugins.input.insns.InsnIndexType;
/** Targeted static inspection. No APK code is executed. Requires the pinned JADX engine. */
class ApkInspector {
  public static void main(String[] args) throws Exception {
    if (args.length < 3) throw new IllegalArgumentException("Usage: ApkInspector APK OUTPUT_DIR CLASS... | @manifest | @smali:CLASS | @find-string:TEXT | @find-call:OWNER->METHOD | @find-type:DEX_TYPE");
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
        if (name.startsWith("@find-string:") || name.startsWith("@find-call:") || name.startsWith("@find-type:")) {
          boolean calls=name.startsWith("@find-call:");
          boolean types=name.startsWith("@find-type:");
          String needle=name.substring(calls || types ? 11 : 13);
          var indexType=calls ? InsnIndexType.METHOD_REF : types ? InsnIndexType.TYPE_REF : InsnIndexType.STRING_REF;
          if(needle.isEmpty()) throw new IllegalArgumentException("Supply a nonempty reference query");
          int[] count={0};
          for(var cls:jadx.getClassesWithInners()) {
            for(var method:cls.getClassNode().getMethods()) {
              var code=method.getCodeReader();
              if(code==null) continue;
              code.visitInstructions(insn -> {
                if(insn.getIndexType()!=indexType) return;
                insn.decode();
                String target;
                if(calls) {
                  var ref=insn.getIndexAsMethod();
                  ref.load();
                  target=ref.getParentClassType()+"->"+ref.getName();
                } else if(types) {
                  target=insn.getIndexAsType();
                } else {
                  target=insn.getIndexAsString();
                }
                if(target.contains(needle)) {
                  if(count[0]<200) System.out.println(cls.getRawName()+"->"+method.getMethodInfo().getShortId()+" @dex-code-unit "+insn.getOffset());
                  count[0]++;
                }
              });
            }
          }
          System.out.println("Reference matches="+count[0]+"; at most 200 sites printed; referenced values omitted");
          continue;
        }
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
