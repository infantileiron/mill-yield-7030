import {api,post,download} from './client.js';
export const batches={list:()=>api('/batches'),create:d=>post('/batches',d)};
export const inspections={list:()=>api('/inspections'),create:d=>{if(!d.sampled_at)delete d.sampled_at;return post('/inspections',d);}};
export const reviews={list:()=>api('/reviews'),get:id=>api('/reviews/'+id),create:d=>post('/reviews',d),approve:(id,note)=>post(`/reviews/${id}/approve`,{note}),download};
export const pairings={list:()=>api('/pairings'),get:id=>api('/pairings/'+id),create:d=>post('/pairings',d)};
