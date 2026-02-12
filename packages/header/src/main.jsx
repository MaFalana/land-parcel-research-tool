import React from "react";
import "./header.css";

export default function HwcHeader({
  logoSrc,
  basePath = "",
  homeHref = "https://www.hwcengineering.com/",
  alt = "HWC Engineering",
  title,
  actions,
  children
}) {
  // Default logo path with base path support
  const defaultLogoSrc = `${basePath}/assets/HWC-Logo-Light.png`;
  const finalLogoSrc = logoSrc || defaultLogoSrc;
  // actions: optional slot for header controls (search, filters, buttons, etc.)
  // children: fallback slot for additional content

  return (
    <header className="hwc-header" role="banner" aria-label="HWC header">
      <div className="hwc-header__inner">
        <div className="hwc-header__left">
          <a className="hwc-header__brand" href={homeHref} aria-label="Home">
            <img className="hwc-header__logo" src={finalLogoSrc} alt={alt} />
          </a>

          {title ? (
            <>
              <span className="hwc-header__sep" aria-hidden="true">|</span>
              <span className="hwc-header__title" title={title}>{title}</span>
            </>
          ) : null}
        </div>

        <div className="hwc-header__actions">
          {actions}
          {children}
        </div>
      </div>
    </header>
  );
}
