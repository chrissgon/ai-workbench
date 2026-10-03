import { Widget } from "../core/widget";

export class Counter extends Widget {
  value = 0;

  mount(): void {
    const button = document.createElement("button");
    button.textContent = String(this.value);
    button.addEventListener("click", () => {
      this.increment();
      button.textContent = String(this.value);
    });
    this.root.append(button);
  }

  increment(): void {
    this.value += 1;
    this.emit();
  }
}
