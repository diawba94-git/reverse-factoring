export const NINEA_PATTERN = /^\d{9}([0-9A-Za-z]{3})?$/;

export function isValidNinea(value: string): boolean {
  return NINEA_PATTERN.test(value.trim());
}

export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function normalizePhone(value: string): string {
  return value.replace(/[\s.-]/g, "");
}

export function isValidPhone(value: string): boolean {
  return /^\+?\d{8,15}$/.test(normalizePhone(value));
}
