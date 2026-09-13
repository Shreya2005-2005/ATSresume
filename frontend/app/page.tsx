import Link from "next/link";
import { Orbitron, Alex_Brush } from "next/font/google";

const orbitron = Orbitron({ subsets: ["latin"], weight: ["700", "800"] });
const alexBrush = Alex_Brush({ subsets: ["latin"], weight: "400" });

export default function HomePage() {
  return (
    <div>
      <section className="relative overflow-hidden rounded-3xl shadow-2xl grid md:grid-cols-[6fr_4fr] min-h-[560px]">
        {/* Left panel — free-license Unsplash underwater photo (photo-1668110648714) */}
        <div className="relative overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/images/hero-ocean.jpg"
            alt=""
            aria-hidden="true"
            className="absolute inset-0 w-full h-full object-cover object-bottom"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950/70 via-slate-950/10 to-transparent" />
          <div className="relative z-10 h-full flex flex-col justify-end px-8 md:px-12 py-14 text-white max-w-sm">
            <h2 className="text-3xl md:text-4xl font-bold leading-tight mb-4">
              Your story
              <br />
              comes in
              <br />
              evidence.
            </h2>
            <p className="text-sm text-teal-50/80 mb-8">
              Paste a job description and Yours Resume tailors a resume straight from your own
              evidence, every claim fact-checked, nothing invented.
            </p>
            <Link
              href="/input"
              className="self-start text-xs font-semibold tracking-[0.2em] uppercase border border-white/60 rounded-full px-6 py-3 hover:bg-white hover:text-teal-800 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>

        {/* Right panel — brand wordmark */}
        <div className="relative bg-slate-900 flex items-center justify-center px-8 md:px-14 py-14">
          <h1 className="leading-tight text-center">
            <span
              className={`${orbitron.className} font-bold uppercase text-4xl md:text-5xl tracking-wide text-white block`}
            >
              Yours
            </span>
            <span
              className={`${alexBrush.className} text-6xl md:text-7xl text-white block -mt-2`}
            >
              Resume
            </span>
          </h1>
        </div>
      </section>
    </div>
  );
}
