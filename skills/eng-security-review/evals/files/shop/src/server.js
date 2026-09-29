import { createServer, json } from "@shopco/http-kit";
import { format } from "@shopco/money";

const app = createServer();
app.use(json({ limit: "1mb" }));
app.get("/orders/:id/total", (req, res) => {
  res.send({ total: format(req.order.total, "BRL") });
});
app.listen(process.env.PORT || 3000);
