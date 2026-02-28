<script lang="ts">
	import { base } from '$app/paths';
	const tiers = [
		{
			id: 'focused',
			name: 'Focused',
			description: 'Single-purpose specialists for specific tasks. ~800 tokens.',
			color: 'bg-green-900/50 text-green-300 border-green-700',
			features: [
				'5-8 instructions maximum',
				'Single operational mode',
				'Minimal configuration',
				'Best for simple, repetitive tasks'
			]
		},
		{
			id: 'expert',
			name: 'Expert',
			description: 'Domain experts with deep specialized knowledge. ~1500 tokens.',
			color: 'bg-blue-900/50 text-blue-300 border-blue-700',
			features: [
				'15-20 instructions',
				'Multiple cognitive modes',
				'Ensemble role support',
				'Best for domain-specific work'
			]
		},
		{
			id: 'phd',
			name: 'PhD',
			description: 'Comprehensive agents with research-grade depth. ~3000 tokens.',
			color: 'bg-purple-900/50 text-purple-300 border-purple-700',
			features: [
				'25+ instructions',
				'Full cognitive mode support',
				'Complex escalation logic',
				'Best for critical decisions'
			]
		}
	];
</script>

<svelte:head>
	<title>Create Agent | Agent Manager</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
	<h1 class="text-2xl font-bold text-gray-100 mb-2">Create New Agent</h1>
	<p class="text-gray-400 mb-8">
		Choose a tier template to start creating your agent. Each tier has different capabilities and complexity.
	</p>

	<div class="grid gap-6">
		{#each tiers as tier}
			<a
				href="{base}/create/{tier.id}"
				class="block p-6 bg-gray-800 border border-gray-700 rounded-lg hover:border-blue-500 hover:bg-gray-750 transition-all"
			>
				<div class="flex items-start gap-4">
					<div class="w-16 h-16 {tier.color} rounded-lg flex items-center justify-center flex-shrink-0 border">
						<span class="text-3xl font-bold">{tier.name.charAt(0)}</span>
					</div>
					<div class="flex-1">
						<h2 class="text-xl font-semibold text-gray-100 mb-1">{tier.name} Tier</h2>
						<p class="text-gray-400 mb-4">{tier.description}</p>
						<ul class="grid grid-cols-2 gap-2">
							{#each tier.features as feature}
								<li class="flex items-center gap-2 text-sm text-gray-400">
									<svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
									</svg>
									{feature}
								</li>
							{/each}
						</ul>
					</div>
					<svg class="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</div>
			</a>
		{/each}
	</div>

	<div class="mt-8 p-4 bg-blue-900/30 border border-blue-700 rounded-lg">
		<h3 class="font-semibold text-blue-300 mb-2">Not sure which tier to choose?</h3>
		<p class="text-blue-200 text-sm">
			Start with <strong>Expert</strong> tier for most use cases. It provides a good balance of capability
			and complexity. Use <strong>Focused</strong> for simple automation tasks and <strong>PhD</strong>
			for critical decision-making agents.
		</p>
	</div>
</div>
