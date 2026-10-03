import { describe, expect, it } from "vitest";
import { Counter } from "../src/widgets/counter";

describe("Counter", () => {
  it("counts each increment and tells its listeners", () => {
    const counter = new Counter({ replaceChildren() {} } as unknown as HTMLElement);
    let calls = 0;
    counter.on(() => { calls += 1; });
    counter.increment();
    counter.increment();
    expect(counter.value).toBe(2);
    expect(calls).toBe(2);
  });
});
