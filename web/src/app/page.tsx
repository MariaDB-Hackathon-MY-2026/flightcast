import { redirect } from "next/navigation";

export default function RootPage() {
  // Time Travel is the hero / default landing page (matches Streamlit's
  // st.Page("pages/02_time_travel.py", default=True))
  redirect("/time-travel");
}
