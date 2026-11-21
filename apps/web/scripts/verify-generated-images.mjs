import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";

const file=new URL("../public/images/generated/bifanas-com-natas.webp",import.meta.url);
const bytes=readFileSync(file);
const expectedHash="38650895acfac74dbaaeb0546a868a06b44705c47d3b60d3831cb892f88b41ca";
const actualHash=createHash("sha256").update(bytes).digest("hex");
if(bytes.toString("ascii",0,4)!=="RIFF" ||
    bytes.toString("ascii",8,12)!=="WEBP" ||
    bytes.readUInt32LE(4)+8!==bytes.length ||
    actualHash!==expectedHash){
  throw new Error("Bifanas illustration missing, incomplete, or altered unexpectedly");
}
console.log("Bifanas WebP verified",bytes.length,"bytes, SHA-256",actualHash);
