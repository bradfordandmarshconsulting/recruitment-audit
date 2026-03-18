import nodemailer from "nodemailer";

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

const raw = await readStdin();
const payload = JSON.parse(raw || "{}");

if (!payload.smtp?.user || !payload.smtp?.pass) {
  throw new Error("SMTP credentials are missing. Set AUDIT_NOTIFICATION_SMTP_USER and AUDIT_NOTIFICATION_SMTP_PASS.");
}

const transporter = nodemailer.createTransport({
  host: payload.smtp.host,
  port: payload.smtp.port,
  secure: false,
  auth: {
    user: payload.smtp.user,
    pass: payload.smtp.pass,
  },
  requireTLS: true,
});

await transporter.sendMail({
  from: payload.from,
  to: payload.to,
  subject: payload.subject,
  text: payload.text,
  attachments: [
    {
      filename: payload.attachmentName,
      path: payload.attachmentPath,
      contentType: "application/pdf",
    },
  ],
});
