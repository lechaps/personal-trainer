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
function htmlForPlainText(title, content) {
  function escape(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  // Leave font selection to Notes; each paragraph uses its native body style.
  var lines = content.replace(/\r\n?/g, '\n').split('\n');
  return '<h1>' + escape(title) + '</h1>' + lines.map(function(line) {
    return '<div>' + (line ? escape(line) : '<br/>') + '</div>';
  }).join('');
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
    if (content.indexOf('SC-ID:') >= 0) throw new Error('Identifiant interne interdit dans le contenu publié');
    var exactMarker = new RegExp('(^|\\n)' + marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(\\r?\\n|$)');
    var existing = notes.filter(function(n) { return exactMarker.test(plain(n)); });
    if (existing.length > 1) throw new Error('Identifiant dupliqué dans Apple Notes : action manuelle requise');
    if (existing.length === 1) return JSON.stringify({status: 'already_exists', note_id: existing[0].id()});
    // Recover retries without exposing an internal identifier in the note.
    var sameTitle = notes.filter(function(n) { return n.name() === title; });
    function normalized(s) { return s.replace(/\r\n?/g, '\n').split('\n').map(function(line) { return line.trim(); }).filter(function(line) { return line; }).join('\n'); }
    if (sameTitle.length > 1) throw new Error('Titre de séance ambigu : action manuelle requise');
    if (sameTitle.length === 1) {
      var actual = normalized(plain(sameTitle[0]));
      if (actual === normalized(content) || actual === normalized(title + '\n' + content)) {
        return JSON.stringify({status: 'already_exists', note_id: sameTitle[0].id()});
      }
      throw new Error('Une séance différente porte déjà ce titre : création annulée');
    }
    var newNote = app.Note({name: title, body: htmlForPlainText(title, content)});
    folder.notes.push(newNote);
    return JSON.stringify({status: 'created', note_id: newNote.id()});
  }
  throw new Error('Opération interdite');
}
