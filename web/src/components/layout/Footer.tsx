import { Clock } from "lucide-react";

export function Footer() {
  return (
    <footer className="mt-12 pt-6 pb-2 text-center">
      <div className="inline-flex items-center gap-1.5 text-xs text-slate-500">
        <Clock size={12} />
        All times shown in Asia/Kuala Lumpur (UTC+8)
      </div>
    </footer>
  );
}
