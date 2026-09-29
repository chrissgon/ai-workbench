export function addNote(notes, text) {
  return [...notes, { id: notes.length + 1, text: text.trim() }];
}
