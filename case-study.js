const data = window.STORY_DATA;
if (!data) throw new Error("Missing generated data/story-data.js");

document.querySelector("#count-all").textContent = data.method.annex_occupation_count;
document.querySelector("#count-exposed").textContent = data.method.exposed_occupation_count;
document.querySelector("#count-examples").textContent = String(data.occupations.length).padStart(2, "0");
document.querySelector("#profile-total").textContent = data.method.annex_occupation_count;
document.querySelector("#qa-count").textContent =
  `${data.quality_check.means_within_0_01}/${data.quality_check.occupation_count}`;
document.querySelector("#qa-code").textContent = data.quality_check.largest_gap.isco08_code;

const profileChart = document.querySelector("#profile-chart");
const maxCount = Math.max(...data.occupation_profile.map((item) => item.count));
const profileFragment = document.createDocumentFragment();
data.occupation_profile.forEach((item) => {
  const row = document.createElement("div");
  row.className = "profile-row";
  const label = document.createElement("span");
  label.textContent = item.label_vi;
  const track = document.createElement("div");
  track.className = "profile-track";
  const fill = document.createElement("i");
  fill.style.width = `${(item.count / maxCount) * 100}%`;
  if (item.group.startsWith("gradient_")) fill.classList.add("profile-fill--exposed");
  track.append(fill);
  const count = document.createElement("b");
  count.textContent = item.count;
  row.append(label, track, count);
  profileFragment.append(row);
});
profileChart.append(profileFragment);
profileChart.setAttribute(
  "aria-label",
  data.occupation_profile.map((item) => `${item.label_vi}: ${item.count} mã nghề`).join("; "),
);

document.querySelector("#case-low-value").textContent = `${data.income.low_pct}%`;
document.querySelector("#case-high-value").textContent = `${data.income.high_pct}%`;
document.querySelector("#case-gap-value").textContent = data.income.gap_pp;
const incomeScale = Math.ceil(data.income.high_pct / 10) * 10;
document.querySelector("#case-low-bar").style.width = `${(data.income.low_pct / incomeScale) * 100}%`;
document.querySelector("#case-high-bar").style.width = `${(data.income.high_pct / incomeScale) * 100}%`;
