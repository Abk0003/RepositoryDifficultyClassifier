const fetchBtn  = document.getElementById("fetch-btn");
const repoUrl   = document.getElementById("repo-url");
const statusMsg = document.getElementById("status-msg");
let pieChart    = null;
let currentRepo = "";

fetchBtn.addEventListener("click", async () => {
    const url = repoUrl.value.trim();

    if (!url) {
        statusMsg.textContent = "Please enter a GitHub URL";
        statusMsg.className = "mt-2 mb-0 text-danger";
        return;
    }

    fetchBtn.disabled    = true;
    fetchBtn.textContent = "Fetching...";
    statusMsg.textContent = "Scraping issues... this may take up to 2 minutes for large repos";
    statusMsg.className   = "mt-2 mb-0 text-muted";

    const controller = new AbortController();
    const timeout    = setTimeout(() => controller.abort(), 120000);

    try {
        const response = await fetch("/api/scrape", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({url: url}),
            signal: controller.signal
        });

        clearTimeout(timeout);
        const data = await response.json();

        if (data.error) {
            statusMsg.textContent = `Error: ${data.error}`;
            statusMsg.className   = "mt-2 mb-0 text-danger";
        } else {
            currentRepo = data.repo;
            statusMsg.textContent = data.message;
            statusMsg.className   = "mt-2 mb-0 text-success";
            document.getElementById("stats-section").classList.remove("d-none");
            document.getElementById("filter-section").classList.remove("d-none");
            document.getElementById("issues-section").classList.remove("d-none");
            loadIssues();
            loadStats();
        }

    } catch (err) {
        console.log("catch error:", err);
        if (err.name === "AbortError") {
            statusMsg.textContent = "Request timed out — try a smaller repo";
        } else {
            statusMsg.textContent = "Failed to connect to server";
        }
        statusMsg.className = "mt-2 mb-0 text-danger";
    } finally {
        fetchBtn.disabled    = false;
        fetchBtn.textContent = "Fetch Issues";
    }
});

function loadIssues() {
    const dif   = document.getElementById("difficulty-filter").value;
    const s     = document.getElementById("search").value.trim();
    const dateF = document.getElementById("date-from").value;
    const dateT = document.getElementById("date-to").value;

    let url = "/api/issues?";
    url += `repo=${currentRepo}&`;
    if (dif)   url += `difficulty=${dif}&`;
    if (s)     url += `search=${s}&`;
    if (dateF) url += `date_from=${dateF}&`;
    if (dateT) url += `date_to=${dateT}&`;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById("issues-body");
            const count = document.getElementById("issue-count");
            tbody.innerHTML = "";
            count.textContent = `(${data.length} issues)`;

            data.forEach(issue => {
                const badge = issue.difficulty === "Easy"   ? "success" :
                              issue.difficulty === "Medium" ? "warning" : "danger";
                const row = `
                    <tr>
                        <td>${issue.title}</td>
                        <td>${issue.repo}</td>
                        <td><span class="badge bg-${badge}">${issue.difficulty}</span></td>
                        <td>${issue.last_updated}</td>
                        <td><a href="${issue.url}" target="_blank">View</a></td>
                    </tr>`;
                tbody.innerHTML += row;
            });
        })
        .catch(err => console.log("loadIssues error:", err));
}

function loadStats() {
    console.log("currentRepo:", currentRepo);
    fetch(`/api/stat?repo=${currentRepo}`)
        .then(res => res.json())
        .then(data => {
            const ctx = document.getElementById("pie-chart").getContext("2d");
            if (pieChart) pieChart.destroy();
            pieChart = new Chart(ctx, {
                type: "pie",
                data: {
                    labels: ["Easy", "Medium", "Hard"],
                    datasets: [{
                        data: [data.Easy, data.Medium, data.Hard],
                        backgroundColor: ["#198754", "#ffc107", "#dc3545"]
                    }]
                },
                options: {
                    plugins: {
                        legend: { position: "bottom" }
                    }
                }
            });
        })
        .catch(err => console.log("loadStats error:", err));
}

document.getElementById("filter-btn").addEventListener("click", () => {
    loadIssues();
});