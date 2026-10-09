// What a file handed to a task needs before it is sent: the refusal the page can know (over 25 MiB, a name the service would refuse) and the
// base64 of its bytes. The Agent tab's "Hand a file over" and the review card's use them; the service checks both again.

export const MAX_FILE_BYTES = 25 * 1024 * 1024;
const NAME = /^[A-Za-z0-9._-]{1,100}$/;

/** The base64 of some bytes (the body of a file handed over): chunked so a large file does not overflow the call stack. */
export function toBase64(bytes) {
  let text = "";
  for (let i = 0; i < bytes.length; i += 0x8000) text += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(text);
}

/** The refusal before sending, or "" when the file may be sent: over 25 MiB, or a name the service would refuse. */
export function fileRefusal(name, size) {
  if (size > MAX_FILE_BYTES) return "A file handed to a task is at most 25 MiB.";
  if (!NAME.test(name)) return "The file name may hold letters, digits, ., _ and -, at most 100 characters.";
  return "";
}
