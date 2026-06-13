import { Outlet } from "react-router-dom";

export default function OperatorLayout() {
  return (
    <div className="theme-operations dark min-h-screen w-full bg-background text-foreground flex flex-col">
      <header className="h-16 border-b border-border bg-card flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-primary">QueueMind</h1>
          <div className="h-6 w-px bg-border"></div>
          <div className="text-sm font-medium">Counter: <span className="text-primary text-lg">2</span></div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-success"></span>
            <span className="text-sm text-muted-foreground">Online</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm">Operator: Sarah J.</div>
        </div>
      </header>
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
