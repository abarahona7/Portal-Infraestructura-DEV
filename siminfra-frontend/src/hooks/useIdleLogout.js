import { useEffect, useRef } from 'react';

const DEFAULT_IDLE_MS = 5 * 60 * 1000;
const ACTIVITY_THROTTLE_MS = 1000;

export const useIdleLogout = ({
  enabled,
  onIdle,
  timeoutMs = DEFAULT_IDLE_MS,
}) => {
  const timerRef = useRef(null);
  const lastResetRef = useRef(0);
  const onIdleRef = useRef(onIdle);

  useEffect(() => {
    onIdleRef.current = onIdle;
  }, [onIdle]);

  useEffect(() => {
    if (!enabled) {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      return undefined;
    }

    const armTimer = (force = false) => {
      const now = Date.now();

      if (!force && now - lastResetRef.current < ACTIVITY_THROTTLE_MS) {
        return;
      }

      lastResetRef.current = now;

      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      timerRef.current = setTimeout(() => {
        onIdleRef.current?.();
      }, timeoutMs);
    };

    const activityEvents = [
      'mousemove',
      'mousedown',
      'keydown',
      'scroll',
      'touchstart',
      'pointerdown',
    ];

    const handleActivity = () => armTimer(false);

    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, handleActivity, { passive: true });
    });

    armTimer(true);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, handleActivity);
      });
    };
  }, [enabled, timeoutMs]);
};
