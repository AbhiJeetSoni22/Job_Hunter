"use client";

import React, { useEffect, useState, HTMLAttributes } from "react";
import { useInView } from "@/hooks/useInView";

interface ScrollRevealProps extends HTMLAttributes<HTMLDivElement> {
  animation?: "fade-up" | "fade" | "scale-in" | "slide-left" | "slide-right";
  delayMs?: number;
  durationMs?: number;
  threshold?: number;
  triggerOnce?: boolean;
}

/**
 * Performant scroll reveal wrapper using IntersectionObserver and CSS hardware-accelerated transforms.
 */
export function ScrollReveal({
  animation = "fade-up",
  delayMs = 0,
  durationMs = 350,
  threshold = 0.12,
  triggerOnce = true,
  children,
  className = "",
  style,
  ...rest
}: ScrollRevealProps) {
  const [ref, isInView] = useInView<HTMLDivElement>({ threshold, triggerOnce });

  const getTransformInit = () => {
    switch (animation) {
      case "fade-up":
        return "translateY(16px)";
      case "scale-in":
        return "scale(0.96)";
      case "slide-left":
        return "translateX(20px)";
      case "slide-right":
        return "translateX(-20px)";
      case "fade":
      default:
        return "none";
    }
  };

  return (
    <div
      ref={ref}
      style={{
        opacity: isInView ? 1 : 0,
        transform: isInView ? "none" : getTransformInit(),
        transition: `opacity ${durationMs}ms cubic-bezier(0.16, 1, 0.3, 1) ${delayMs}ms, transform ${durationMs}ms cubic-bezier(0.16, 1, 0.3, 1) ${delayMs}ms`,
        willChange: isInView ? "auto" : "opacity, transform",
        ...style,
      }}
      className={className}
      {...rest}
    >
      {children}
    </div>
  );
}

interface ScoreRingProps {
  score: number | null;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  animate?: boolean;
}

const ringSizes = {
  sm: { diameter: 44, strokeWidth: 3.5, fontSize: "0.75rem", labelSize: "0.6rem" },
  md: { diameter: 58, strokeWidth: 4, fontSize: "0.95rem", labelSize: "0.65rem" },
  lg: { diameter: 76, strokeWidth: 5, fontSize: "1.25rem", labelSize: "0.7rem" },
};

/**
 * Animated SVG circular score progress ring.
 * Animates stroke-dashoffset from 0% to the target score when scrolled into view.
 */
export function ScoreRing({
  score,
  size = "md",
  showLabel = false,
  animate = true,
}: ScoreRingProps) {
  const [ref, isInView] = useInView<HTMLDivElement>({ threshold: 0.1, triggerOnce: true });
  const [displayedScore, setDisplayedScore] = useState(animate ? 0 : score ?? 0);

  const { diameter, strokeWidth, fontSize, labelSize } = ringSizes[size];
  const radius = (diameter - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const validScore = score !== null && !isNaN(score) ? Math.min(100, Math.max(0, score)) : null;

  useEffect(() => {
    if (!isInView || validScore === null) return;
    if (!animate) {
      setDisplayedScore(validScore);
      return;
    }

    // Check prefers-reduced-motion
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setDisplayedScore(validScore);
      return;
    }

    const duration = 650;
    const start = performance.now();

    const frame = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(1, elapsed / duration);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayedScore(Math.round(eased * validScore));

      if (progress < 1) {
        requestAnimationFrame(frame);
      }
    };

    requestAnimationFrame(frame);
  }, [isInView, validScore, animate]);

  // Color by tier
  const strokeColor =
    validScore === null
      ? "var(--color-muted)"
      : validScore >= 70
        ? "var(--color-green)"
        : validScore >= 40
          ? "var(--color-amber)"
          : "var(--color-red)";

  const strokeDashoffset =
    validScore === null
      ? circumference
      : circumference - (circumference * displayedScore) / 100;

  return (
    <div
      ref={ref}
      className="inline-flex flex-col items-center justify-center relative flex-shrink-0"
      style={{ width: diameter, height: diameter }}
      aria-label={validScore !== null ? `Match score: ${validScore}%` : "Not scored"}
      role="progressbar"
      aria-valuenow={validScore ?? 0}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <svg
        width={diameter}
        height={diameter}
        className="-rotate-90 transform"
        style={{ width: diameter, height: diameter }}
      >
        {/* Track circle */}
        <circle
          cx={diameter / 2}
          cy={diameter / 2}
          r={radius}
          stroke="var(--color-surface-hover)"
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Animated fill circle */}
        <circle
          cx={diameter / 2}
          cy={diameter / 2}
          r={radius}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="none"
          style={{
            transition: "stroke-dashoffset 200ms ease, stroke 300ms ease",
          }}
        />
      </svg>

      {/* Centered score number */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center select-none pointer-events-none">
        <span
          style={{
            fontSize,
            fontWeight: 800,
            lineHeight: 1,
            color: validScore !== null ? "var(--color-text)" : "var(--color-muted)",
          }}
        >
          {validScore !== null ? `${displayedScore}%` : "—"}
        </span>
        {showLabel && validScore !== null && (
          <span
            style={{
              fontSize: labelSize,
              color: strokeColor,
              fontWeight: 600,
              marginTop: "2px",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            {validScore >= 70 ? "High" : validScore >= 40 ? "Med" : "Low"}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Animated number counter that counts up to target value when in view.
 */
export function AnimatedCounter({
  value,
  durationMs = 600,
  suffix = "",
  prefix = "",
}: {
  value: number;
  durationMs?: number;
  suffix?: string;
  prefix?: string;
}) {
  const [ref, isInView] = useInView<HTMLSpanElement>({ threshold: 0.1, triggerOnce: true });
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (!isInView) return;

    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setCurrent(value);
      return;
    }

    const start = performance.now();
    const frame = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(1, elapsed / durationMs);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(eased * value));

      if (progress < 1) {
        requestAnimationFrame(frame);
      }
    };

    requestAnimationFrame(frame);
  }, [isInView, value, durationMs]);

  return (
    <span ref={ref}>
      {prefix}
      {current}
      {suffix}
    </span>
  );
}
