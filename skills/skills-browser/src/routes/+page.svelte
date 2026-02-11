<script lang="ts">
	export let data;

	let searchTerm = '';
	let typeFilter = '';
	let selectedSkill = null;

	$: filteredSkills = data.skills.filter(skill => {
		const matchesSearch = !searchTerm ||
			skill.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
			skill.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
			skill.category.toLowerCase().includes(searchTerm.toLowerCase());

		const matchesType = !typeFilter || skill.type === typeFilter;

		return matchesSearch && matchesType;
	});

	function openSkill(skill) {
		selectedSkill = skill;
	}

	function closeModal() {
		selectedSkill = null;
	}
</script>

<svelte:head>
	<title>Skills Browser - 84 Specialized Skills</title>
</svelte:head>

<div class="container">
	<header class="header">
		<div class="header-content">
			<h1 class="title">⚡ Skills Library</h1>
			<p class="subtitle">{data.skills.length} specialized skills for tactical operations and community workflows</p>
		</div>
	</header>

	<div class="filters">
		<input
			type="text"
			class="search-input"
			placeholder="Search skills..."
			bind:value={searchTerm}
		/>
		<select class="filter-select" bind:value={typeFilter}>
			<option value="">All Types</option>
			<option value="tactical">Tactical</option>
			<option value="community">Community</option>
		</select>
	</div>

	<div class="skills-grid">
		{#each filteredSkills as skill (skill.id)}
			<button class="skill-card" on:click={() => openSkill(skill)}>
				<div class="skill-header">
					<h3 class="skill-name">{skill.name}</h3>
					<span class="skill-badge {skill.type}">{skill.type}</span>
				</div>
				<p class="skill-description">{skill.description}</p>
				<div class="skill-meta">
					<span class="meta-item">🤖 {skill.model}</span>
					{#if skill.tools && skill.tools.length > 0}
						<span class="meta-item">🔧 {skill.tools.join(', ')}</span>
					{/if}
					{#if skill.context}
						<span class="meta-item">📍 {skill.context}</span>
					{/if}
				</div>
				<div class="skill-footer">
					<span class="category-label">{skill.category}</span>
				</div>
			</button>
		{/each}
	</div>

	{#if filteredSkills.length === 0}
		<div class="empty-state">
			<p>No skills found matching your search.</p>
		</div>
	{/if}
</div>

{#if selectedSkill}
	<div class="modal-overlay" on:click={closeModal}>
		<div class="modal-content" on:click|stopPropagation>
			<div class="modal-header">
				<h2 class="modal-title">{selectedSkill.name}</h2>
				<button class="modal-close" on:click={closeModal}>&times;</button>
			</div>
			<div class="modal-body">
				<pre class="skill-content">{selectedSkill.content}</pre>
			</div>
		</div>
	</div>
{/if}

<style>
	.container {
		padding: 24px;
		max-width: 1400px;
		margin: 0 auto;
	}

	.header {
		margin-bottom: 32px;
	}

	.title {
		font-size: 32px;
		font-weight: 700;
		color: #b0b0b0;
		margin-bottom: 8px;
	}

	.subtitle {
		font-size: 16px;
		color: #808080;
	}

	.filters {
		display: flex;
		gap: 12px;
		margin-bottom: 24px;
	}

	.search-input {
		flex: 1;
		background: #0f0f0f;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
		padding: 12px 16px;
		color: #b0b0b0;
		font-size: 14px;
		font-family: 'Nunito', sans-serif;
	}

	.search-input:focus {
		outline: none;
		border-color: #4a4a4a;
	}

	.filter-select {
		background: #0f0f0f;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
		padding: 12px 16px;
		color: #b0b0b0;
		font-size: 14px;
		font-family: 'Nunito', sans-serif;
		cursor: pointer;
	}

	.filter-select:focus {
		outline: none;
		border-color: #4a4a4a;
	}

	.skills-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 16px;
	}

	.skill-card {
		background: #0f0f0f;
		border: 1px solid #2a2a2a;
		border-radius: 12px;
		padding: 20px;
		text-align: left;
		cursor: pointer;
		transition: all 0.2s;
		width: 100%;
	}

	.skill-card:hover {
		border-color: #4a4a4a;
		background: #1a1a1a;
	}

	.skill-header {
		display: flex;
		justify-content: space-between;
		align-items: start;
		margin-bottom: 12px;
	}

	.skill-name {
		font-size: 18px;
		font-weight: 600;
		color: #b0b0b0;
		margin: 0;
	}

	.skill-badge {
		padding: 4px 12px;
		border-radius: 6px;
		font-size: 11px;
		font-weight: 500;
		text-transform: uppercase;
	}

	.skill-badge.tactical {
		background: #1a3a1a;
		color: #4ade80;
	}

	.skill-badge.community {
		background: #1a1a3a;
		color: #818cf8;
	}

	.skill-description {
		color: #808080;
		font-size: 14px;
		line-height: 1.5;
		margin-bottom: 16px;
	}

	.skill-meta {
		display: flex;
		gap: 12px;
		flex-wrap: wrap;
		margin-bottom: 16px;
	}

	.meta-item {
		font-size: 12px;
		color: #707070;
	}

	.skill-footer {
		display: flex;
		gap: 8px;
		align-items: center;
	}

	.category-label {
		font-size: 11px;
		color: #606060;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.empty-state {
		text-align: center;
		padding: 60px 20px;
		color: #707070;
	}

	/* Modal */
	.modal-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.8);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 20px;
	}

	.modal-content {
		background: #0f0f0f;
		border: 1px solid #2a2a2a;
		border-radius: 12px;
		max-width: 900px;
		width: 100%;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 20px 24px;
		border-bottom: 1px solid #2a2a2a;
	}

	.modal-title {
		font-size: 24px;
		font-weight: 600;
		color: #b0b0b0;
		margin: 0;
	}

	.modal-close {
		background: none;
		border: none;
		color: #b0b0b0;
		font-size: 32px;
		cursor: pointer;
		padding: 0;
		width: 36px;
		height: 36px;
		border-radius: 6px;
		transition: all 0.2s;
	}

	.modal-close:hover {
		background: rgba(50, 50, 50, 0.3);
	}

	.modal-body {
		padding: 24px;
		overflow-y: auto;
		flex: 1;
	}

	.skill-content {
		font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
		font-size: 13px;
		line-height: 1.6;
		color: #a0a0a0;
		white-space: pre-wrap;
		word-wrap: break-word;
	}
</style>
