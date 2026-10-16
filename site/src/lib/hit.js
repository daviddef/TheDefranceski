/* A "where this name appears" excerpt on a /who/ page.
 *
 * The excerpts in dossiers.json were cut from page data by flattening whole
 * objects into text, so a snippet taken from a table of records reads
 *   "…, id: 6VYQ-7DJZ , name: Albin Franceschini , sex: Male , birth: 1898 ,
 *    christening: , marriage: , death: , burial: , place: , spouses: …"
 * and one taken from a timeline reads ", key: true , y: 1716 , t: A hundred
 * thousand ducats , w: On 16 July …". That is the field names of the archive's
 * own data files printed at the reader (81 name pages, 325 excerpts).
 *
 * The data is left exactly as it is; this turns an excerpt that has the
 * signature of a flattened object into a readable line: internal fields (ids,
 * flags, urls, empty values) are dropped, genealogical fields get a short label
 * ("b.", "d.", "spouses"), everything else is shown as its bare value, and the
 * pieces are joined with " · ". An excerpt of ordinary prose is returned
 * untouched.
 */
const DROP = new Set([
  "id", "gid", "famc", "fams", "key", "ours", "line", "conn", "conf", "href", "url",
  "thumb", "plates", "group", "fatherKey", "motherKey", "deathYear", "birthYear",
  "bornExact", "spelling", "region", "by", "dy", "n", "kids", "children", "rows",
  "plot", "country", "cites", "sex", "title2",
]);
const LABEL = {
  birth: "b.", born: "b.", christening: "chr.", marriage: "m.", death: "d.", died: "d.",
  burial: "bur.", place: "at", spouses: "spouses", parents: "parents",
  father: "father", mother: "mother", note: "", notes: "",
};
const KNOWN = [...new Set([...DROP, ...Object.keys(LABEL),
  "name", "who", "what", "dates", "where", "field", "text", "title", "caption", "lab", "t", "w", "y",
  "d", "a", "b", "from", "to", "lead", "story", "why", "when", "link", "slug", "alt", "holder",
  "src", "cap", "kind", "page", "label", "role"])].sort((x, y) => y.length - x.length).join("|");
/* The flattening joined fields with " , " (space, comma, space), which prose
   never does, and sometimes with a bare ", " between short scalar fields. */
const ANYKEY = "[A-Za-z_][A-Za-z0-9_]{0,24}";
const SPLIT = new RegExp(`\\s,\\s(?=${ANYKEY}:\\s?)|,\\s(?=(?:${KNOWN}):\\s?)`);
const PAIR = new RegExp(`^(${ANYKEY}):\\s?([\\s\\S]*)$`);
const EMPTY = /^(?:|null|undefined|true|false|\[\]|\{\})$/;

export const tidyHit = (text) => {
  const raw = String(text ?? "");
  const parts = raw.split(SPLIT);
  const pairs = parts.filter((s) => PAIR.test(s)).length;
  if (parts.length < 3 || pairs < 2) return raw;     // prose, not a flattened object
  const out = [];
  for (let i = 0; i < parts.length; i++) {
    // The excerpt is cut at a fixed length, often through the next field name
    // (" , place: , s"): drop that stump from the last piece.
    const seg = i === parts.length - 1 ? parts[i].replace(/\s,\s?[^\s,:]{0,24}$/, "") : parts[i];
    let v = seg.trim(), k = null, lab = "", dropped = false;
    // "spouse: name: Anna" — wrappers around the value; peel them off.
    for (let guard = 0; guard < 4; guard++) {
      const m = v.match(PAIR);
      if (!m) break;
      if (k === null) k = m[1];
      if (DROP.has(m[1])) dropped = true;
      if (LABEL[m[1]]) lab = LABEL[m[1]];
      v = m[2].trim();
    }
    v = v.replace(/\s+,\s*$/, "").trim();
    if (dropped || EMPTY.test(v)) continue;
    out.push(lab ? `${lab} ${v}` : v);
  }
  return out.join(" · ");
};
