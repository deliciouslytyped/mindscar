Mine DAMNED scanner and archiver - because doing this with a lot of documents on a slow scanner is terribly boring

todo: create an example annex repo

labelmaker:
  for printing document labels
  [todo insert generated screenshot]
  
scanflow:
  for scanning documents
  [todo insert generated screenshot]

  manages a flow for scanning while committing scanned documents to a git-annex repository. runs a server to scan scan codes with the Binary Eye app (has batch mode, background url submission pending)
  the app is run in a xephyr window running a python repl and using feh for preview thumbnails and viewing the scan

  flow:
    scan code
    run "scan" to scan a page, page is added to D$ID folder automatically
    scan next code - documents are committed to git-annex between switch operations

  technical notes:
    the codebase is rushed and rickety, no resilience should be expected

    feh is restarted any time i deemed an update necessary, the refresh feature doesnt work with thumbnails (yet)?
    im open to suggestions for a component that can provide better interactive thumbnail and browsing capability, for QC of the scanned materials while scanning.
    extra points for integrated cropping capability? for interesting features, explore scantailor and scantailor-advanced (both are for scanning books)


principles:
  modifiable and fixable with standard tools
    reasons:
      my tooling will always ve lacking due to dev time
  high flexibility and capability data structures
    git, git-annex
    libreoffice calc for document db? (coming up with own sql stuff too tedious and restricted without a lot of work)
  crash friendly, should be able to close at any point
