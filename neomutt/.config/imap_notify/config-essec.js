var child_process = require('child_process');
 
function getStdout(cmd) {
    var stdout = child_process.execSync(cmd);
    return stdout.toString().trim();
}

exports.host = "imap.gmail.com"
exports.port = 993;
exports.tls = true;
exports.tlsOptions = { "rejectUnauthorized": false };
exports.username = "b00755043@essec.edu";
exports.password = getStdout("pass mutt/essec.edu");
exports.onNotify = "mbsync essec-inbox"
exports.onNotifyPost = { "mail": "notify-send 'New Mail (ESSEC)'" };
exports.boxes = [ "INBOX" ];

