export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ message: 'Method Not Allowed' });
    }

    const token = process.env.GITHUB_TOKEN;
    const owner = "BERSERKYT";
    const repo = "GoldSignalBot";
    const workflow_id = "scan.yml";

    if (!token) {
        return res.status(500).json({ message: "Server configuration error: GITHUB_TOKEN missing." });
    }

    try {
        const response = await fetch(
            `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow_id}/dispatches`,
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ref: 'main'
                })
            }
        );

        if (!response.ok) {
            const errorText = await response.text();
            console.error('GitHub API error:', errorText);
            return res.status(response.status).json({ message: `GitHub API error: ${response.status}`, details: errorText });
        }

        return res.status(200).json({ message: 'Scan triggered successfully' });
    } catch (error) {
        console.error('Fetch error:', error);
        return res.status(500).json({ message: 'Internal Server Error', error: error.message });
    }
}
