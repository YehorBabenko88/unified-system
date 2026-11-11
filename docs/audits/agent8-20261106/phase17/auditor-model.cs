
namespace A8Independent {
 using System;using System.Collections.Generic;using MathUniverse.Agent7;
 public class P:ITracePlatform {
  public Queue<TraceEvent> Q=new Queue<TraceEvent>();public List<uint> S=new List<uint>();public long Clock;public bool Child=true,FailBegin,FailFinish,FailClose,ExitStop=true;public int Stops,Finishes;public uint Budget;
  public long Now{get{return Clock;}}public bool HasChild{get{return Child;}}
  public bool Begin(){if(FailBegin)throw new Exception();return true;}
  public bool Wait(out TraceEvent e,uint ms){if(ms>100)throw new Exception();Clock+=ms;e=Q.Count==0?null:Q.Dequeue();return e!=null;}
  public bool Continue(TraceEvent e,uint status){S.Add(status);return true;}
  public bool CloseImage(TraceEvent e){return !FailClose;}
  public bool Stop(){Stops++;if(ExitStop)Q.Enqueue(E(5,0));return true;}
  public bool Finish(uint ms,bool exit){Finishes++;Budget=ms;return !FailFinish&&(!Child||exit);}
  public static TraceEvent E(uint kind,uint code){return new TraceEvent{Kind=kind,Pid=7,Tid=9,Code=code,FirstChance=1,Module="OS_NTDLL"};}
 }
 public static class Checks {
  static void Need(bool b){if(!b)throw new Exception("A8_MODEL_FAIL");}
  public static string Run(){int n=0;
   var p=new P();p.Q.Enqueue(P.E(3,0));p.Q.Enqueue(P.E(1,0x80000003));p.Q.Enqueue(P.E(1,0x80000003));p.Q.Enqueue(P.E(5,71));var r=LoaderInitTrace.Observe(p);Need(r.Cleanup&&p.S[1]==0x10002&&p.S[2]==0x80010001&&r.FirstException=="BREAKPOINT"&&r.Outcome=="DEBUGGER_PERTURBED_BASELINE");n++;
   p=new P();p.Q.Enqueue(P.E(1,0xc0000005));r=LoaderInitTrace.Observe(p);Need(r.Cleanup&&r.Outcome=="PROTOCOL_FAILURE"&&p.S[0]==0x80010001);n++;
   p=new P();p.Child=false;p.FailBegin=true;r=LoaderInitTrace.Observe(p);Need(r.Cleanup&&p.Stops==1&&p.Finishes==1&&r.Outcome=="PROTOCOL_FAILURE");n++;
   p=new P();p.Q.Enqueue(P.E(3,0));r=LoaderInitTrace.Observe(p);Need(r.Cleanup&&r.Outcome=="DEADLINE"&&p.Clock<=15000&&p.Budget<=5000);n++;
   p=new P();p.FailFinish=true;p.Q.Enqueue(P.E(3,0));p.Q.Enqueue(P.E(5,0));r=LoaderInitTrace.Observe(p);Need(!r.Cleanup&&r.Outcome=="CLEANUP_UNCONFIRMED");n++;
   p=new P();p.FailClose=true;p.Q.Enqueue(P.E(3,0));p.Q.Enqueue(P.E(5,0));r=LoaderInitTrace.Observe(p);Need(!r.Cleanup&&r.Outcome=="CLEANUP_UNCONFIRMED");n++;
   p=new P();p.ExitStop=false;p.Q.Enqueue(P.E(3,0));r=LoaderInitTrace.Observe(p);Need(!r.Cleanup&&p.Clock<=15000&&p.Stops==1&&p.Finishes==1);n++;
   return "A8_MODEL_ONLY cases="+n+" nativeInvocations=0";
  }
 }
}
