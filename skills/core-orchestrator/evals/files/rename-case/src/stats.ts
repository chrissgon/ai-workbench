export function summarize(events: { user: string }[]) {
  const usrCnt = new Set(events.map((e) => e.user)).size;
  return { users: usrCnt, total: events.length };
}
