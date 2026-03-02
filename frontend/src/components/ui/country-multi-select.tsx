"use client";

import { useState } from "react";
import { XIcon, PlusIcon, CheckIcon } from "lucide-react";
import { COUNTRIES, countryByCode } from "@/lib/countries";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

type Props = {
  value: string[]; // array of ISO codes
  onChange: (codes: string[]) => void;
  disabled?: boolean;
  placeholder?: string;
};

export function CountryMultiSelect({
  value,
  onChange,
  disabled,
  placeholder = "Add country…",
}: Props) {
  const [open, setOpen] = useState(false);

  function handleSelect(code: string) {
    if (value.includes(code)) {
      onChange(value.filter((c) => c !== code));
    } else {
      onChange([...value, code]);
    }
  }

  function handleRemove(code: string) {
    onChange(value.filter((c) => c !== code));
  }

  return (
    <div className="space-y-2">
      {/* Tags */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((code) => {
            const country = countryByCode(code);
            return (
              <span
                key={code}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-primary/10 border border-primary/25 text-primary"
              >
                {country ? `${country.name} (${code})` : code}
                {!disabled && (
                  <button
                    type="button"
                    onClick={() => handleRemove(code)}
                    className="hover:text-destructive transition-colors ml-0.5"
                    aria-label={`Remove ${code}`}
                  >
                    <XIcon className="size-3" />
                  </button>
                )}
              </span>
            );
          })}
        </div>
      )}

      {/* Add button */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-dashed border-border/60 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground transition-colors disabled:opacity-50"
      >
        <PlusIcon className="size-3.5" />
        {placeholder}
      </button>

      <CommandDialog
        open={open}
        onOpenChange={setOpen}
        title="Select countries"
        description="Search and select one or more countries"
        showCloseButton={false}
      >
        <CommandInput placeholder="Search countries…" />
        <CommandList>
          <CommandEmpty>No country found.</CommandEmpty>
          <CommandGroup>
            {COUNTRIES.map((country) => {
              const selected = value.includes(country.code);
              return (
                <CommandItem
                  key={country.code}
                  value={`${country.name} ${country.code}`}
                  onSelect={() => handleSelect(country.code)}
                  className="cursor-pointer"
                >
                  <span className="flex-1">
                    {country.name}
                    <span className="ml-2 text-xs text-muted-foreground font-mono">
                      {country.code}
                    </span>
                  </span>
                  {selected && <CheckIcon className="size-4 text-primary" />}
                </CommandItem>
              );
            })}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </div>
  );
}
