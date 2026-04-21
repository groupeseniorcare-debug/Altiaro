import React from "react";
import { InstagramLogo, Heart } from "@phosphor-icons/react";

/**
 * Instagram / UGC grid — 6 tuiles carrées de contenu communauté.
 * design.instagram = { handle, posts: [{ image, href, likes }] }
 */
export default function InstagramGrid({ instagram, design }) {
  const primary = design?.brand?.primary_color || "#B84B31";
  const fontHeading = design?.brand?.font_heading || "Fraunces";

  const handle = instagram?.handle || "@sereniva.fr";
  const posts = instagram?.posts?.length
    ? instagram.posts
    : [
        { image: "https://images.unsplash.com/photo-1505330622279-bf7d7fc918f4?w=600&auto=format&fit=crop", likes: 342 },
        { image: "https://images.unsplash.com/photo-1487956382158-bb926046304a?w=600&auto=format&fit=crop", likes: 218 },
        { image: "https://images.unsplash.com/photo-1483058712412-4245e9b90334?w=600&auto=format&fit=crop", likes: 156 },
        { image: "https://images.unsplash.com/photo-1544027993-37dbfe43562a?w=600&auto=format&fit=crop", likes: 489 },
        { image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600&auto=format&fit=crop", likes: 271 },
        { image: "https://images.unsplash.com/photo-1566753323558-f4e0952af115?w=600&auto=format&fit=crop", likes: 198 },
      ];

  return (
    <section className="py-20 md:py-24 px-6 bg-white" data-testid="storefront-instagram">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 text-[11px] uppercase tracking-[0.2em] text-neutral-500 mb-3">
            <InstagramLogo size={14} weight="duotone" />
            Notre communauté
          </div>
          <h2 className="text-4xl md:text-5xl mb-3" style={{ fontFamily: `${fontHeading}, serif`, color: "#1C1917" }}>
            Suivez-nous sur Instagram
          </h2>
          <a
            href={instagram?.url || `https://instagram.com/${handle.replace("@", "")}`}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium hover:underline"
            style={{ color: primary }}
            data-testid="instagram-handle"
          >
            {handle}
          </a>
        </div>

        <div className="grid grid-cols-3 md:grid-cols-6 gap-1.5 md:gap-3">
          {posts.slice(0, 6).map((p, i) => (
            <a
              key={i}
              href={p.href || "#"}
              target="_blank"
              rel="noreferrer"
              data-testid={`instagram-post-${i}`}
              className="group relative aspect-square overflow-hidden rounded-xl bg-neutral-100"
            >
              <img
                src={p.image}
                alt={`Post ${i + 1}`}
                loading="lazy"
                className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors duration-300 flex items-center justify-center">
                <div className="opacity-0 group-hover:opacity-100 transition-opacity text-white text-sm font-medium flex items-center gap-1.5">
                  <Heart size={16} weight="fill" />
                  {p.likes}
                </div>
              </div>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
