/*
 * Apple Notes adapter (JXA / osascript on macOS).
 * Usage: osascript -l JavaScript jxa/notes.js <list|create> /private/path/request.json
 * Only reads notes in one existing account and folder. Never updates or deletes notes.
 * This has not been integration-tested against the user's macOS installation.
 */
ObjC.import('Foundation');

function readJSON(path) {
  var content = $.NSString.stringWithContentsOfFileEncodingError(
    $(path), $.NSUTF8StringEncoding, null
  );
  if (!content) throw new Error('Impossible de lire la requête locale');
  return JSON.parse(ObjC.unwrap(content));
}
function nonempty(value, field) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('Champ invalide: ' + field);
  return value;
}
function folderFor(notesApp, accountName, folderName) {
  var accounts = notesApp.accounts().filter(function(a) { return a.name() === accountName; });
  if (accounts.length !== 1) throw new Error('Compte Apple Notes introuvable ou ambigu');
  var folders = accounts[0].folders().filter(function(f) { return f.name() === folderName; });
  if (folders.length !== 1) throw new Error('Dossier Notes introuvable ou ambigu (utiliser un dossier simple à la racine)');
  return folders[0];
}
function plain(note) {
  // Notes exposes plaintext and body (HTML); the MVP supports textual notes only.
  var s = note.plaintext();
  if (typeof s !== 'string') throw new Error('Note sans contenu texte exploitable');
  return s;
}
function htmlForPlainText(content) {
  function escape(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  return '<html><body><div style="font-family:-apple-system,Helvetica,sans-serif;white-space:pre-wrap">' +
    escape(content).replace(/\r\n?/g, '\n').replace(/\n/g, '<br/>') + '</div></body></html>';
}
function run(argv) {
  if (argv.length !== 2) throw new Error('Arguments: <list|create> <request.json>');
  var op = argv[0], req = readJSON(argv[1]);
  var account = nonempty(req.account, 'account');
  var folderName = nonempty(req.folder, 'folder');
  var app = Application('Notes');
  var folder = folderFor(app, account, folderName);
  var notes = folder.notes();
  if (op === 'list') {
    var records = notes.map(function(n) {
      return {
        id: n.id(), title: n.name(), text: plain(n),
        modified: n.modificationDate().toISOString()
      };
    });
    return JSON.stringify({notes: records});
  }
  if (op === 'create') {
    var stableId = nonempty(req.sc_id, 'sc_id');
    if (!/^sc-[a-f0-9-]{8,64}$/.test(stableId)) throw new Error('SC-ID invalide');
    var title = nonempty(req.title, 'title');
    var content = nonempty(req.text, 'text');
    var marker = 'SC-ID: ' + stableId;
    if (content.indexOf(marker) < 0) throw new Error('Marqueur SC-ID absent du brouillon');
    var exactMarker = new RegExp('(^|\\n)' + marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(\\r?\\n|$)');
    var existing = notes.filter(function(n) { return exactMarker.test(plain(n)); });
    if (existing.length > 1) throw new Error('Identifiant dupliqué dans Apple Notes : action manuelle requise');
    if (existing.length === 1) return JSON.stringify({status: 'already_exists', note_id: existing[0].id()});
    var newNote = app.Note({name: title, body: htmlForPlainText(content)});
    folder.notes.push(newNote);
    return JSON.stringify({status: 'created', note_id: newNote.id()});
  }
  throw new Error('Opération interdite');
}
