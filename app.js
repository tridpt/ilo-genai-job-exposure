const storyData = window.STORY_DATA;
if (!storyData) throw new Error("Missing generated data/story-data.js");

const chapters = [...document.querySelectorAll(".chapter")];
const panels = [...document.querySelectorAll(".viz")];
const stageFrame = document.querySelector("#stage-frame");
const stageCounter = document.querySelector("#stage-counter");
const stageFooter = document.querySelector("#stage-footer-label");
const progressFill = document.querySelector("#progress-fill");
const heroGrid = document.querySelector("#hero-dot-grid");
const peopleGrid = document.querySelector("#people-grid");

const footerLabels = [
  "Một phần tư công việc trên toàn cầu",
  "Tiếp xúc cao không đồng nghĩa mất việc",
  "Mỗi nền kinh tế, một cơ cấu nghề",
  "Sự khác biệt trong việc làm của từng giới",
  "Chỉ số nói về tiềm năng tác động",
];

// The generated data records the rounding used by the 100-cell illustration.
function createDots(container) {
  const fragment = document.createDocumentFragment();
  const mediumStart = storyData.global.grid.outside;
  const highStart = mediumStart + storyData.global.grid.gradients_1_3;
  for (let index = 0; index < 100; index += 1) {
    const cell = document.createElement("span");
    cell.className = "data-cell";
    if (index >= mediumStart && index < highStart)
      cell.classList.add("data-cell--medium");
    if (index >= highStart) cell.classList.add("data-cell--high");
    cell.style.setProperty("--delay", `${Math.max(0, index - mediumStart) * 28}ms`);
    fragment.append(cell);
  }
  container.append(fragment);
}

createDots(heroGrid);
createDots(peopleGrid);
const storyDots = [...peopleGrid.children].slice(storyData.global.grid.outside);

let activeIndex = -1;
let scrollFrame = 0;

function activate(index) {
  if (index === activeIndex) return;
  activeIndex = index;
  panels.forEach((panel, panelIndex) => {
    panel.hidden = panelIndex !== index;
  });
  chapters.forEach((chapter, chapterIndex) => {
    chapter.classList.toggle("is-active", chapterIndex === index);
  });
  stageFrame.dataset.active = String(index);
  stageCounter.textContent = `${index + 1} trong 5`;
  stageFooter.textContent = footerLabels[index];
}

function updateOnScroll() {
  scrollFrame = 0;
  const pageRange = document.documentElement.scrollHeight - innerHeight;
  const pageProgress = pageRange > 0 ? scrollY / pageRange : 0;
  progressFill.style.transform = `scaleX(${Math.max(0, Math.min(1, pageProgress))})`;

  const targetY = innerHeight * (innerWidth <= 820 ? 0.72 : 0.52);
  let closestIndex = 0;
  let closestDistance = Infinity;
  chapters.forEach((chapter, index) => {
    const rect = chapter.getBoundingClientRect();
    const distance =
      rect.top <= targetY && rect.bottom >= targetY
        ? 0
        : Math.min(
            Math.abs(rect.top - targetY),
            Math.abs(rect.bottom - targetY),
          );
    if (distance < closestDistance) {
      closestIndex = index;
      closestDistance = distance;
    }
  });
  activate(closestIndex);

  const rect = chapters[closestIndex].getBoundingClientRect();
  const draw = Math.max(
    0,
    Math.min(1, (innerHeight * 0.92 - rect.top) / (innerHeight * 0.55)),
  );
  stageFrame.style.setProperty("--draw", String(draw));
  storyDots.forEach((cell, index) => {
    cell.classList.toggle(
      "is-revealed",
      closestIndex !== 0 || index < Math.round(draw * storyDots.length),
    );
  });
}

addEventListener(
  "scroll",
  () => {
    if (!scrollFrame) scrollFrame = requestAnimationFrame(updateOnScroll);
  },
  { passive: true },
);
addEventListener("resize", updateOnScroll);
updateOnScroll();

const genderData = storyData.gender;
const genderButtons = [...document.querySelectorAll(".gender-toggle button")];
const femaleValue = document.querySelector("#female-value");
const maleValue = document.querySelector("#male-value");
const femaleBar = document.querySelector("#female-bar");
const maleBar = document.querySelector("#male-bar");
const formatPercent = (value) => `${value.toFixed(1).replace(".", ",")}%`;

genderButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const values = genderData[button.dataset.scope];
    genderButtons.forEach((candidate) => {
      const selected = candidate === button;
      candidate.classList.toggle("is-selected", selected);
      candidate.setAttribute("aria-pressed", String(selected));
    });
    femaleValue.textContent = formatPercent(values.female);
    maleValue.textContent = formatPercent(values.male);
    femaleBar.style.setProperty("--bar-width", `${values.female * 10}%`);
    maleBar.style.setProperty("--bar-width", `${values.male * 10}%`);
  });
});

const guessAnswer = storyData.income.high_pct;
const guessCard = document.querySelector(".guess-card");
const guessRange = document.querySelector("#guess-range");
const guessValue = document.querySelector("#guess-value");
const guessGrid = document.querySelector("#guess-grid");
const guessGridLabel = document.querySelector("#guess-grid-label");
const guessGridCaption = document.querySelector("#guess-grid-caption");
const guessSubmit = document.querySelector("#guess-submit");
const guessResult = document.querySelector("#guess-result");
const guessYours = document.querySelector("#guess-yours");
const guessCompare = document.querySelector("#guess-compare");
const guessFeedback = document.querySelector("#guess-feedback");
const guessReset = document.querySelector("#guess-reset");
const incomePanel = document.querySelector(".viz--income");
const incomeAxisLabels = [...document.querySelectorAll("#income-axis span")];
const incomeBarLow = document.querySelector("#income-bar-low");
const incomeBarHigh = document.querySelector("#income-bar-high");
const incomeGuessMarker = document.querySelector("#income-guess-marker");
const incomeGuessNote = document.querySelector("#income-guess-note");
const incomeGuessValue = document.querySelector("#income-guess-value");
const incomeGuessDifference = document.querySelector(
  "#income-guess-difference",
);
const guessCells = Array.from({ length: 100 }, () => {
  const cell = document.createElement("span");
  guessGrid.append(cell);
  return cell;
});

function updateGuessGrid(count, className) {
  guessCells.forEach((cell, index) => {
    cell.classList.toggle(
      "is-guessed",
      className === "is-guessed" && index < count,
    );
    cell.classList.toggle(
      "is-actual",
      className === "is-actual" && index < count,
    );
  });
}

function updateGuess() {
  const value = Number(guessRange.value);
  guessValue.textContent = String(value);
  guessRange.style.setProperty("--guess-position", `${value}%`);
  guessRange.setAttribute("aria-valuetext", `${value} trên 100 lao động`);
  updateGuessGrid(value, "is-guessed");
}

function updateIncomeComparison(value = null) {
  const hasGuess = value !== null;
  const baselineScale = Math.ceil(storyData.income.high_pct / 10) * 10;
  const scale =
    !hasGuess || value <= baselineScale
      ? baselineScale
      : Math.ceil(value / 20) * 20;
  incomeAxisLabels.forEach((label, index) => {
    label.textContent = `${(index * scale) / 4}${index === 4 ? "%" : ""}`;
  });
  incomeBarLow.style.setProperty(
    "--bar-width",
    `${(storyData.income.low_pct / scale) * 100}%`,
  );
  incomeBarHigh.style.setProperty(
    "--bar-width",
    `${(storyData.income.high_pct / scale) * 100}%`,
  );
  incomePanel.classList.toggle("has-guess", hasGuess);
  incomeGuessMarker.hidden = !hasGuess;
  incomeGuessNote.hidden = !hasGuess;

  if (!hasGuess) {
    incomePanel.setAttribute(
      "aria-label",
      `Tỷ lệ việc làm trong các nhóm tiếp xúc là ${storyData.income.low_pct}% ở nước thu nhập thấp và ${storyData.income.high_pct}% ở nước thu nhập cao`,
    );
    return;
  }

  const difference = Math.abs(value - guessAnswer);
  const comparison =
    difference === 0
      ? `trùng với ước tính ${guessAnswer}% của ILO.`
      : `${value > guessAnswer ? "cao hơn" : "thấp hơn"} mức ${guessAnswer}% của ILO ${difference} điểm phần trăm.`;
  incomeGuessMarker.style.setProperty(
    "--guess-position",
    `${(value / scale) * 100}%`,
  );
  incomeGuessValue.textContent = `${value}%`;
  incomeGuessDifference.textContent = comparison;
  incomePanel.setAttribute(
    "aria-label",
    `Thu nhập thấp ${storyData.income.low_pct}%; thu nhập cao ${storyData.income.high_pct}%; bạn đoán ${value}%, ${comparison} Trục từ 0 đến ${scale}%.`,
  );
}

guessRange.addEventListener("input", updateGuess);
guessSubmit.addEventListener("click", () => {
  const value = Number(guessRange.value);
  const difference = Math.abs(value - guessAnswer);
  const direction = value < guessAnswer ? "thấp hơn" : "cao hơn";

  guessRange.disabled = true;
  guessCard.classList.add("is-revealed");
  guessYours.textContent = String(value);
  guessCompare.style.setProperty("--your-position", `${value}%`);
  guessCompare.setAttribute(
    "aria-label",
    `Bạn đoán ${value} trên 100; ILO ước tính ${guessAnswer} trên 100; chênh lệch ${difference}.`,
  );
  guessGridLabel.textContent = "Ước tính ILO";
  guessGridCaption.textContent =
    `${guessAnswer} ô sáng: tỷ lệ việc làm ở nghề có tiếp xúc với AI tạo sinh.`;
  updateGuessGrid(guessAnswer, "is-actual");
  guessFeedback.textContent =
    (difference === 0
      ? `Bạn đoán trúng ${guessAnswer} trên 100! `
      : `${difference <= 5 ? "Rất gần! " : ""}Dự đoán của bạn ${direction} ước tính ILO ${difference} người trên 100. `) +
    "Đây là mức tiếp xúc của nghề, không phải tỷ lệ mất việc.";
  updateIncomeComparison(value);
  guessSubmit.hidden = true;
  guessResult.hidden = false;
  guessFeedback.focus();
});

guessReset.addEventListener("click", () => {
  guessRange.value = "25";
  guessRange.disabled = false;
  guessCard.classList.remove("is-revealed");
  guessGridLabel.textContent = "Dự đoán của bạn";
  guessGridCaption.textContent =
    "Mỗi ô sáng tương ứng một người trong dự đoán của bạn.";
  guessFeedback.textContent = "";
  guessResult.hidden = true;
  guessSubmit.hidden = false;
  updateIncomeComparison();
  updateGuess();
  guessRange.focus();
});
updateGuess();

const occupationRows = document.querySelector("#occupation-rows");
const occupationChart = document.querySelector(".occupation-chart");
const occupationFragment = document.createDocumentFragment();
storyData.occupations.forEach((occupation) => {
  const row = document.createElement("div");
  row.className = "occupation-row";
  row.dataset.isco = occupation.isco08_code;
  row.style.setProperty("--score", `${occupation.mean_score * 100}%`);
  row.style.setProperty("--row-color", occupation.color);

  const name = document.createElement("div");
  name.className = "occupation-name";
  const title = document.createElement("strong");
  title.textContent = occupation.label_vi;
  const group = document.createElement("small");
  group.textContent = occupation.group_label_vi;
  name.append(title, group);

  const track = document.createElement("div");
  track.className = "occupation-track";
  track.append(document.createElement("span"));
  const score = document.createElement("b");
  score.textContent = occupation.mean_score.toFixed(2).replace(".", ",");
  row.append(name, track, score);
  occupationFragment.append(row);
});
occupationRows.append(occupationFragment);
occupationChart.setAttribute(
  "aria-label",
  "Điểm nhiệm vụ trung bình: " +
    storyData.occupations
      .map((item) => `${item.label_vi} ${item.mean_score.toFixed(2).replace(".", ",")}`)
      .join("; "),
);

const occupationSection = document.querySelector(".occupation");
if ("IntersectionObserver" in window) {
  const occupationObserver = new IntersectionObserver(
    (entries, observer) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        occupationSection.classList.add("is-visible");
        observer.disconnect();
      }
    },
    { threshold: 0.15 },
  );
  occupationObserver.observe(occupationSection);
} else {
  occupationSection.classList.add("is-visible");
}
