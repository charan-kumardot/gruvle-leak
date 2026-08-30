import Image from "next/image";

export function Logo({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <Image
      src="/logo-mark.svg"
      alt=""
      width={size}
      height={size}
      className={`shrink-0 rounded-lg ${className}`}
      priority
    />
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <Logo size={26} />
      <span className="font-semibold tracking-tight">Gruvle Leak</span>
    </span>
  );
}
