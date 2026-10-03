export type Listener = () => void;

export abstract class Widget {
  private listeners: Listener[] = [];

  constructor(protected readonly root: HTMLElement) {}

  abstract mount(): void;

  on(listener: Listener): void {
    this.listeners.push(listener);
  }

  protected emit(): void {
    for (const listener of this.listeners) listener();
  }

  destroy(): void {
    this.listeners = [];
    this.root.replaceChildren();
  }
}
