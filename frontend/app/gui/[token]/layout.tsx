import type {Metadata} from "next";
export const metadata: Metadata = {title: "Gửi yêu cầu làm video", description: "Kể cho studio nghe video bạn cần.", robots: {index: false, follow: false}};
export default function GuiLayout({children}: Readonly<{children: React.ReactNode}>) {return children;}
