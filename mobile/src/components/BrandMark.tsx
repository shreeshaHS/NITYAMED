/** Official NityaMed Vector Logo Symbol (Continuity Loop + Safety Shield + Dual Capsule + Chime Node). */

import React from 'react';
import Svg, { Circle, G, Path } from 'react-native-svg';

interface BrandMarkProps {
  size?: number;
  variant?: 'default' | 'inverse';
}

export function BrandMark({ size = 40, variant = 'default' }: BrandMarkProps) {
  const mainTeal = variant === 'inverse' ? '#FFFFFF' : '#0D6E6E';
  const emerald = variant === 'inverse' ? '#34D399' : '#10B981';
  const pillTop = variant === 'inverse' ? '#0D6E6E' : '#FFFFFF';

  return (
    <Svg width={size} height={size} viewBox="0 0 512 512" fill="none">
      {/* Continuous Daily Continuity Loop */}
      <Path
        d="M 402.6 370.5 A 186 186 0 1 1 288.3 72.8"
        stroke={mainTeal}
        strokeWidth={38}
        strokeLinecap="round"
        fill="none"
      />
      {/* Scheduled Reminder Chime Pulse Node */}
      <Circle cx={337.5} cy={88.8} r={15} fill={emerald} />
      {/* Active Clockwise Cadence Arc + Arrow */}
      <Path
        d="M 380.5 117.8 A 186 186 0 0 1 439.2 223.7"
        stroke={emerald}
        strokeWidth={38}
        strokeLinecap="round"
        fill="none"
      />
      <Path
        d="M 407.5 227.5 L 472.5 218.5 L 444.0 272.0 Z"
        fill={emerald}
        stroke={emerald}
        strokeWidth={10}
        strokeLinejoin="round"
      />
      {/* Patient Protection Shield */}
      <Path
        d="M 256 126 C 308 126 348 139 363 149 C 370 154 372 161 372 171 L 372 250 C 372 322 317 372 264 395 C 258 398 254 398 248 395 C 195 372 140 322 140 250 L 140 171 C 140 161 142 154 149 149 C 164 139 204 126 256 126 Z"
        fill={mainTeal}
      />
      {/* Tilted Dual-Tone Medicine Capsule */}
      <G transform="translate(256 248) rotate(-45)">
        <Path d="M -29 -58 A 29 29 0 0 1 29 -58 L 29 -4 L -29 -4 Z" fill={pillTop} />
        <Path d="M -29 4 L 29 4 L 29 58 A 29 29 0 0 1 -29 58 Z" fill={emerald} />
      </G>
    </Svg>
  );
}
