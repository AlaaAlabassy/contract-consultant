import type { Metadata } from "next";
import { Noto_Kufi_Arabic } from "next/font/google";
import "./globals.css";

const arabicFont = Noto_Kufi_Arabic({ subsets: ["arabic"], weight: ["400", "500", "700"] });

export const metadata: Metadata = {
  title: "مستشار العقود",
  description: "وكيل عقود ومطالبات ذكي",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body className={arabicFont.className}>{children}</body>
    </html>
  );
}
