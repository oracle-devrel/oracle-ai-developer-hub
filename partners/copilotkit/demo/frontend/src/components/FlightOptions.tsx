"use client";

import type { Flight } from "@/lib/flights";
import { formatTime, stopsLabel } from "@/lib/flights";

export function FlightCard({ flight }: { flight: Flight }) {
  const isNonstop = flight.stops === 0;

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-4 flex items-start gap-4">
      {/* Left: route + times */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-gray-900 text-sm">{flight.airline}</span>
          <span className="text-xs text-gray-400 font-mono">{flight.flight_no}</span>
        </div>

        <div className="text-base font-bold text-gray-900 mb-1">
          {flight.origin} → {flight.destination}
        </div>

        <div className="flex items-center gap-2 text-sm text-gray-600 flex-wrap mb-2">
          <span className="tabular-nums">{formatTime(flight.depart)}</span>
          <span className="text-gray-300">–</span>
          <span className="tabular-nums">{formatTime(flight.arrive)}</span>
          <span className="text-gray-400">·</span>
          <span>{flight.duration}</span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
              isNonstop
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : "bg-amber-50 text-amber-700 border border-amber-200"
            }`}
          >
            {stopsLabel(flight.stops)}
          </span>
          <span className="text-xs text-gray-500 border border-gray-200 rounded-full px-2 py-0.5">
            {flight.cabin}
          </span>
        </div>

        {flight.notes && (
          <p className="mt-2 text-xs text-gray-400 truncate">{flight.notes}</p>
        )}
      </div>

      {/* Right: price + id */}
      <div className="flex flex-col items-end shrink-0 gap-1">
        <span className="text-xl font-bold text-indigo-600 tabular-nums">
          {typeof flight.price_usd === "number" ? `$${flight.price_usd.toLocaleString()}` : "—"}
        </span>
        <span className="text-[10px] text-gray-300 font-mono">{flight.id}</span>
      </div>
    </div>
  );
}

export function FlightOptions({ flights = [] }: { flights?: Flight[] }) {
  if (flights.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-2">No flights found.</p>
    );
  }

  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-gray-500 mb-2">✈️ Flight options</p>
      <div className="grid gap-3">
        {flights.map((flight, i) => (
          <FlightCard key={flight.id ?? `${flight.flight_no ?? "flight"}-${i}`} flight={flight} />
        ))}
      </div>
    </div>
  );
}
