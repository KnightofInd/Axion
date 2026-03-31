"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "axion:user_email";

export function useAxionEmail() {
  const [email, setEmail] = useState("");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setEmail(stored);
      return;
    }

    const preset = process.env.NEXT_PUBLIC_AXION_DEFAULT_EMAIL ?? "";
    if (preset) {
      setEmail(preset);
      window.localStorage.setItem(STORAGE_KEY, preset);
    }
  }, []);

  const saveEmail = (next: string) => {
    const clean = next.trim();
    setEmail(clean);
    if (clean) {
      window.localStorage.setItem(STORAGE_KEY, clean);
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  };

  return { email, saveEmail };
}
