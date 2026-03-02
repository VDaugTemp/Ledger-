"use client";

import { useState } from "react";
import { CheckIcon, ChevronsUpDownIcon } from "lucide-react";
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
  value: string | undefined;
  onChange: (code: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
};

export function CountryCombobox({
  value,
  onChange,
  disabled,
  placeholder = "Select country…",
  className,
}: Props) {
  const [open, setOpen] = useState(false);
  const selected = value ? countryByCode(value) : undefined;

  function handleSelect(code: string) {
    onChange(code);
    setOpen(false);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        className={[
          "flex w-full items-center justify-between rounded-lg border border-border/50 bg-transparent px-3 py-2 text-sm transition-colors",
          "hover:border-primary/40 focus:outline-none focus:border-primary/50 disabled:opacity-50",
          selected ? "text-foreground/85" : "text-muted-foreground/60",
          className ?? "",
        ].join(" ")}
      >
        <span>
          {selected ? `${selected.name} (${selected.code})` : placeholder}
        </span>
        <ChevronsUpDownIcon className="size-4 shrink-0 opacity-40" />
      </button>

      <CommandDialog
        open={open}
        onOpenChange={setOpen}
        title="Select country"
        description="Search for a country by name or code"
        showCloseButton={false}
      >
        <CommandInput placeholder="Search countries…" />
        <CommandList>
          <CommandEmpty>No country found.</CommandEmpty>
          <CommandGroup>
            {COUNTRIES.map((country) => (
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
                {value === country.code && (
                  <CheckIcon className="size-4 text-primary" />
                )}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
