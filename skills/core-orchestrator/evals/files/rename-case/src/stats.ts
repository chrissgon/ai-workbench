export function summarize(events: { user: string }[]) {
  const usrCnt = new Set(events.map((e) => e.user)).size;
  return { usrCnt, total: events.length };
}
