import React, { useState } from "react";
import { ShoppingBagOpen, MagnifyingGlassPlus, X } from "@phosphor-icons/react";

/**
 * Premium product gallery — image principale + vignettes + zoom modal.
 */
export default function ProductGallery({ images = [], name, design }) {
  const primary = "#0A0A0A";
  const accent = "#F5F5F5";
  const [idx, setIdx] = useState(0);
  const [zoomOpen, setZoomOpen] = useState(false);

  const hasImages = images && images.length > 0;
  const activeImg = hasImages ? images[idx] : null;

  return (
    <div className="md:sticky md:top-24" data-testid="product-gallery">
      {/* Main image */}
      <div
        className="aspect-square overflow-hidden relative group mb-3"
        style={{ background: accent, borderRadius: "2px" }}
      >
        {activeImg ? (
          <>
            <img
              src={activeImg}
              alt={`${name} — vue ${idx + 1}`}
              className="w-full h-full object-cover"
              loading="eager"
            />
            <button
              type="button"
              onClick={() => setZoomOpen(true)}
              className="absolute top-4 right-4 w-10 h-10 bg-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition shadow-sm"
              style={{ color: primary, borderRadius: "2px" }}
              aria-label="Agrandir"
              data-testid="gallery-zoom"
            >
              <MagnifyingGlassPlus size={16} weight="regular" />
            </button>
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center" style={{ color: "#D4D4D4" }}>
            <ShoppingBagOpen size={80} weight="thin" />
          </div>
        )}
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="grid grid-cols-5 gap-2" data-testid="gallery-thumbs">
          {images.slice(0, 5).map((img, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setIdx(i)}
              data-testid={`gallery-thumb-${i}`}
              className="aspect-square overflow-hidden transition"
              style={{
                background: accent,
                borderRadius: "2px",
                border: `1.5px solid ${i === idx ? primary : "transparent"}`,
              }}
              aria-label={`Vue ${i + 1}`}
            >
              <img src={img} alt="" className="w-full h-full object-cover" loading="lazy" />
            </button>
          ))}
        </div>
      )}

      {/* Zoom modal */}
      {zoomOpen && activeImg && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-6"
          onClick={() => setZoomOpen(false)}
          data-testid="gallery-zoom-modal"
        >
          <button
            type="button"
            onClick={() => setZoomOpen(false)}
            className="absolute top-5 right-5 w-11 h-11 rounded-full bg-white/10 text-white flex items-center justify-center hover:bg-white/20"
            aria-label="Fermer"
          >
            <X size={22} />
          </button>
          <img
            src={activeImg}
            alt={name}
            className="max-w-full max-h-full object-contain"
            style={{ borderRadius: "2px" }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
      {/* design prop kept for interface parity */}
      {false && <span style={{ background: design ? "" : "" }} />}
    </div>
  );
}
