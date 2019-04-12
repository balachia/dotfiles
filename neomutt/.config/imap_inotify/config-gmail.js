var child_process = require('child_process');
 
function getStdout(cmd) {
    var stdout = child_process.execSync(cmd);
    return stdout.toString().trim();
}

exports.host = "imap.gmail.com"
exports.port = 993;
exports.tls = true;
exports.tlsOptions = { "rejectUnauthorized": false };
exports.username = "avashevko@gmail.com";
exports.password = getStdout("pass mutt/gmail.com");
exports.onNotify = "mbsync gmail-inbox"
exports.onNotifyPost = { "mail": "notify-send 'New Mail (Gmail)'" };
exports.boxes = [ "INBOX" ];

