import React, { useState } from 'react';

export default function Tooltip({ text, children }) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative inline-block">
      <span
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="cursor-help inline-flex items-center"
      >
        {children}
        <span className="ml-1 text-gray-500 text-xs">ℹ️</span>
      </span>
      {show && (
        <div className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg shadow-lg whitespace-nowrap">
          {text}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
            <div className="border-4 border-transparent border-t-gray-800"></div>
          </div>
        </div>
      )}
    </div>
  );
}
