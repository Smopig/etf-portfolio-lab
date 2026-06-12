import SideNav from "./SideNav";
import TopBar from "./TopBar";

export interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen flex-col">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <SideNav />
        <main className="flex-1 overflow-y-auto px-space-6 py-space-8">{children}</main>
      </div>
    </div>
  );
}
