export function route(){const page=location.hash.slice(1)||'batches';return ['batches','inspections','diagnosis','pairing','reports'].includes(page)?page:'batches';}
