/* /roots/lines.json: the lines drawing (/lines/) as data, for the Tree Canvas's Lines mode (which is written to read it; the /roots/ PAGE itself was removed on 23 Nov 2026, this data address stays).

   It is rivers.json as the /lines/ page draws it: the lanes (a status and the years the evidence reaches, the dated places along each, where each goes), the pens of
   households not yet placed on any lane, and the bridges the archive has argued between them. Nothing is added or worked out here. The pens' `members` are person
   ids from the roster, derived by scripts/build-rivers-members.py and held free of living people by the kit's lines gate (checklines.py, P3 and E1), so this file
   names nobody the /lines/ page does not. The lanes carry no member list on purpose: which people stood on which lane is the archive's judgement, and the canvas
   only shows who the tree records at a lane's places, labelled as that. */
import rivers from "../../data/rivers.json";

const { title, caption, unplacedAfter, lanes, pens, bridges } = rivers;

export const GET = () =>
  new Response(JSON.stringify({ v: 1, kind: "lines", host: "archive.defranceski.com", title, caption, unplacedAfter, lanes, pens, bridges }), {
    headers: { "content-type": "application/json; charset=utf-8" },
  });
