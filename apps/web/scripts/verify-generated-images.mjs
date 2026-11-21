import {readFileSync,readdirSync} from "node:fs";
import {createHash} from "node:crypto";

const directory=new URL("../public/images/generated/",import.meta.url);
const files=readdirSync(directory).filter(name=>name.endsWith(".webp"));
if (!files.includes("bifanas-com-natas.webp")) {
  throw new Error("Missing required Bifanas illustration");
}
for (const name of files) {
  const bytes=readFileSync(new URL(name,directory));
  if (bytes.length<1024 || bytes.length>10_000_000 ||
      bytes.toString("ascii",0,4)!=="RIFF" ||
      bytes.toString("ascii",8,12)!=="WEBP" ||
      bytes.readUInt32LE(4)+8!==bytes.length) {
    throw new Error(`Invalid or truncated generated WebP: ${name}`);
  }
  console.log("Verified generated WebP",name,bytes.length,
    createHash("sha256").update(bytes).digest("hex"));
}
console.log(`Verified ${files.length} generated recipe illustration(s)`);
