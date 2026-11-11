/* What is new here, and the archive in numbers: the kit computes it at build time from this archive's own logs (kit/docs/whats-new.md).
   This file is the only Defranceschi-specific part: which JSON is which, and the counts no log holds. (Until 11 November 2026 this
   archive carried the prototype of the whole library here; it is the kit's now.) */
import { buildPulse } from "@daviddef/archive-kit/lib/pulse.js";
import searched from "../data/searched.json";
import corrections from "../data/corrections.json";
import worklist from "../data/worklist.json";
import roster from "../data/roster.json";
import sources from "../data/sources.json";

export const pulse = buildPulse({
  searched, corrections, worklist,
  counts: {
    people: (roster.rows || []).length,
    sources: Array.isArray(sources) ? sources.length : (sources.rows || []).length,
  },
});
