import type { Metadata } from "next";
import { Noto_Kufi_Arabic } from "next/font/google";
import "./globals.css";
import NavBar from "@/components/NavBar";

const arabicFont = Noto_Kufi_Arabic({ subsets: ["arabic"], weight: ["400", "500", "700"] });

export const metadata: Metadata = {
  title: "مستشار العقود",
  description: "وكيل عقود ومطالبات ذكي",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body className={arabicFont.className}>
        <div className="flex h-screen flex-col">
          <NavBar />
          <main className="flex-1 overflow-hidden">{children}</main>
        </div>
      </body>
    </html>
  );
}
