const iconPaths = {
  plus: (
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>
  ),
  refresh: (
    <>
      <path d="M21 12a9 9 0 0 1-15.4 6.4" />
      <path d="M3 12a9 9 0 0 1 15.4-6.4" />
      <path d="M18 2v4h-4" />
      <path d="M6 22v-4h4" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5" />
      <path d="M12 8h.01" />
    </>
  ),
  close: (
    <>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </>
  ),
  check: (
    <path d="m20 6-11 11-5-5" />
  ),
  camera: (
    <>
      <path d="M15 8h1.8a3 3 0 0 1 3 3v5a3 3 0 0 1-3 3H7.2a3 3 0 0 1-3-3v-5a3 3 0 0 1 3-3H9" />
      <path d="m9 8 1.4-2h3.2L15 8" />
      <circle cx="12" cy="13.5" r="3" />
    </>
  ),
  activity: (
    <path d="M3 12h4l3-8 4 16 3-8h4" />
  ),
}

export default function Icon({ name, size = 18, className = '', strokeWidth = 2 }) {
  return (
    <svg
      className={className ? `icon ${className}` : 'icon'}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {iconPaths[name]}
    </svg>
  )
}
