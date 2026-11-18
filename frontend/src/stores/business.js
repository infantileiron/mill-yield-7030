import {batches,inspections,reviews,pairings} from '../api/business.js';
export const state={user:null,batches:[],inspections:[],reviews:[],pairings:[],selected:null,selectedPairing:null};
export async function refresh(){[state.batches,state.inspections,state.reviews,state.pairings]=await Promise.all([batches.list(),inspections.list(),reviews.list(),pairings.list()]);if(state.selected)state.selected=await reviews.get(state.selected.id);if(state.selectedPairing)state.selectedPairing=await pairings.get(state.selectedPairing.id);}
