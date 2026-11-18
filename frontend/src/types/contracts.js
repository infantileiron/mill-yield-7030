/** @typedef {{id:number,code:string,line:string,supplier:string,tonnes:number,received_date:string,samples:number}} Batch */
/** @typedef {{sample_code:string,batch_id:number,flour_yield:number,moisture:number,inspector:string,sampled_at:string|null}} Inspection */
/** @typedef {{id:number,title:string,line:string,status:string,result:object,note:string}} Review */
/** @typedef {{id:number,title:string,line:string,status:string,adjusted_at:string,window_hours:number,moisture_tolerance:number,accepted_at:string,result:object,note:string}} Pairing */
export const API_VERSION='1';
