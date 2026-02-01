"""
Web-Based Claim Verifier (Ollama Only)
- Scrapes web for evidence
- Scores sources by credibility
- Uses local Ollama LLM to understand scraped content
- Builds confidence from real web data
"""

import json
import time
import logging
import re
import os
import requests
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class WebScraper:
    """Scrapes web for evidence"""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    def search_duckduckgo(self, query: str, num_results: int = 8) -> list:
        """Search DuckDuckGo and return URLs"""
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            for result in soup.select('.result'):
                url_elem = result.select_one('.result__url')
                if url_elem:
                    href = url_elem.get_text().strip()
                    if href:
                        if not href.startswith('http'):
                            href = 'https://' + href
                        results.append(href)
                        continue
                
                link = result.select_one('.result__a')
                if link:
                    href = link.get('href', '')
                    if 'uddg=' in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if 'uddg' in parsed:
                            href = urllib.parse.unquote(parsed['uddg'][0])
                    if href and href.startswith('http'):
                        results.append(href)
            
            seen = set()
            unique_results = []
            for r in results:
                if r not in seen:
                    seen.add(r)
                    unique_results.append(r)
            
            return unique_results[:num_results]
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    def search_with_fallback(self, query: str, num_results: int = 8) -> list:
        """Search with fallback to direct Wikipedia"""
        results = self.search_duckduckgo(query, num_results)
        
        if not results:
            wiki_query = query.replace(' ', '_')
            results = [
                f"https://en.wikipedia.org/wiki/{quote_plus(wiki_query)}",
                f"https://www.britannica.com/search?query={quote_plus(query)}"
            ]
        
        return results
    
    def scrape_page(self, url: str) -> dict:
        """Scrape content from a single page"""
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=8)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe']):
                tag.decompose()
            
            title = soup.find('title')
            title = title.get_text().strip() if title else ""
            
            content = ""
            for selector in ['article', 'main', '.content', '#content', '.post', '.entry', '.mw-parser-output']:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text(separator=' ', strip=True)
                    break
            
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text(separator=' ', strip=True)
            
            content = re.sub(r'\s+', ' ', content)
            content = content[:5000]
            
            return {
                "url": url,
                "title": title[:200],
                "content": content,
                "success": True
            }
        except Exception as e:
            logger.debug(f"Scrape error for {url}: {e}")
            return {"url": url, "title": "", "content": "", "success": False}
    
    def scrape_multiple(self, urls: list) -> list:
        """Scrape multiple URLs in parallel"""
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.scrape_page, url): url for url in urls}
            for future in as_completed(futures, timeout=30):
                try:
                    result = future.result()
                    if result["success"] and result["content"]:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Scrape thread error: {e}")
        return results


class SourceScorer:
    """Scores sources by credibility"""
    
    TIER_1 = {
        'wikipedia.org', 'britannica.com', 'gov', 'edu',
        'who.int', 'un.org', 'worldbank.org', 'imf.org',
        'nature.com', 'science.org', 'ieee.org', 'acm.org',
        'reuters.com', 'apnews.com', 'bbc.com', 'bbc.co.uk',
    }
    
    TIER_2 = {
        'nytimes.com', 'washingtonpost.com', 'theguardian.com',
        'wsj.com', 'economist.com', 'forbes.com', 'bloomberg.com',
        'nasa.gov', 'nih.gov', 'cdc.gov', 'fda.gov',
        'mit.edu', 'stanford.edu', 'harvard.edu', 'oxford.ac.uk',
        'sciencedirect.com', 'springer.com', 'wiley.com',
    }
    
    TIER_3 = {
        'cnn.com', 'nbcnews.com', 'abcnews.com', 'cbsnews.com',
        'usatoday.com', 'time.com', 'newsweek.com',
        'techcrunch.com', 'wired.com', 'arstechnica.com',
        'nationalgeographic.com', 'smithsonianmag.com',
        'investopedia.com', 'healthline.com', 'mayoclinic.org',
    }
    
    TIER_4 = {
        'medium.com', 'quora.com', 'reddit.com',
        'businessinsider.com', 'huffpost.com', 'vox.com',
        'theverge.com', 'engadget.com', 'cnet.com',
        'webmd.com', 'medicalnewstoday.com',
    }
    
    def get_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            domain = domain.replace('www.', '')
            return domain
        except:
            return ""
    
    def score_source(self, url: str) -> dict:
        domain = self.get_domain(url)
        
        for site in self.TIER_1:
            if site in domain or domain.endswith('.gov') or domain.endswith('.edu'):
                return {"domain": domain, "score": 100, "tier": "Highly Authoritative"}
        
        for site in self.TIER_2:
            if site in domain:
                return {"domain": domain, "score": 85, "tier": "Very Reliable"}
        
        for site in self.TIER_3:
            if site in domain:
                return {"domain": domain, "score": 70, "tier": "Reliable"}
        
        for site in self.TIER_4:
            if site in domain:
                return {"domain": domain, "score": 50, "tier": "Moderate"}
        
        return {"domain": domain, "score": 30, "tier": "Unverified Source"}


class ClaimVerifier:
    """Main verifier: scrapes web, scores sources, uses Ollama to analyze"""
    
    AMBIGUOUS_WORDS = [
        'increased', 'decreased', 'improved', 'declined', 'grew', 'reduced',
        'significantly', 'substantially', 'considerably', 'greatly', 'slightly',
        'mostly', 'mainly', 'generally', 'usually', 'often', 'sometimes',
        'many', 'few', 'several', 'some', 'most', 'numerous',
        'better', 'worse', 'more', 'less', 'higher', 'lower',
        'around', 'approximately', 'about', 'nearly', 'almost',
        'rapidly', 'slowly', 'quickly', 'gradually',
        'experts say', 'studies show', 'research suggests', 'reportedly',
    ]
    
    def __init__(self):
        self.ollama_model = "llama3.2:3b"
        self.ollama_url = "http://localhost:11434/api/generate"
        self.scraper = WebScraper()
        self.scorer = SourceScorer()
    
    def query_ollama(self, prompt: str) -> str:
        """Query local Ollama LLM"""
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 600
                    }
                },
                timeout=90
            )
            response.raise_for_status()
            return response.json().get('response', '')
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return ""
    
    def is_ambiguous(self, claim: str) -> tuple:
        """Check for ambiguous words"""
        claim_lower = claim.lower()
        matched = []
        for word in self.AMBIGUOUS_WORDS:
            if re.search(r'\b' + re.escape(word) + r'\b', claim_lower):
                matched.append(word)
        return (len(matched) > 0, matched)
    
    def analyze_evidence(self, claim: str, evidence: list) -> dict:
        """Use Ollama to analyze scraped evidence against claim"""
        
        evidence_text = ""
        for i, e in enumerate(evidence[:4], 1):
            evidence_text += f"\n\nSOURCE {i} ({e['source_info']['domain']}):\n"
            evidence_text += f"Content: {e['content'][:1000]}\n"
        
        prompt = f"""You are a fact-checker. Compare the claim with the web evidence and determine if it's true or false.

CLAIM: "{claim}"

WEB EVIDENCE:{evidence_text}

Based on the evidence, respond with ONLY a JSON object:
{{"verdict": "SUPPORTED" or "CONTRADICTED" or "PARTIALLY_SUPPORTED", "confidence": 0-100, "correction": "the correct information if claim is wrong" or null, "key_facts": ["fact from source 1", "fact from source 2"]}}

JSON response:"""

        try:
            text = self.query_ollama(prompt)
            
            if not text:
                return self._analyze_without_llm(claim, evidence)
            
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            return self._analyze_without_llm(claim, evidence)
            
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return self._analyze_without_llm(claim, evidence)
    
    def _analyze_without_llm(self, claim: str, evidence: list) -> dict:
        """Keyword matching fallback when LLM fails"""
        claim_words = set(w.lower() for w in claim.split() if len(w) > 3)
        
        support_count = 0
        for e in evidence[:5]:
            content_lower = e['content'].lower()
            matches = sum(1 for word in claim_words if word in content_lower)
            if matches > len(claim_words) * 0.4:
                support_count += 1
        
        ratio = support_count / len(evidence) if evidence else 0
        
        if ratio >= 0.5:
            return {"verdict": "SUPPORTED", "confidence": int(ratio * 80), "correction": None, "key_facts": []}
        else:
            return {"verdict": "CONTRADICTED", "confidence": 50, "correction": "Unable to verify - check sources", "key_facts": []}
    
    def verify_single_claim(self, claim: str) -> dict:
        """Verify a single claim using web evidence"""
        start_time = time.time()
        
        # Check ambiguity
        is_ambiguous, matched_words = self.is_ambiguous(claim)
        if is_ambiguous:
            return {
                "claim": claim,
                "status": "ambiguous",
                "confidence_score": 0,
                "correction": None,
                "explanation": f"Contains vague terms: {', '.join(matched_words)}. Cannot verify.",
                "ambiguous_words": matched_words,
                "sources": [],
                "key_facts": [],
                "processing_time": round(time.time() - start_time, 2)
            }
        
        # Search the web
        search_query = claim
        urls = self.scraper.search_with_fallback(search_query, num_results=6)
        
        if not urls:
            return {
                "claim": claim,
                "status": "unverifiable",
                "confidence_score": 0,
                "correction": None,
                "explanation": "Could not find web sources",
                "sources": [],
                "key_facts": [],
                "processing_time": round(time.time() - start_time, 2)
            }
        
        # Scrape pages
        scraped = self.scraper.scrape_multiple(urls)
        
        if not scraped:
            return {
                "claim": claim,
                "status": "unverifiable",
                "confidence_score": 0,
                "correction": None,
                "explanation": "Could not retrieve content from sources",
                "sources": [],
                "key_facts": [],
                "processing_time": round(time.time() - start_time, 2)
            }
        
        # Score sources
        evidence = []
        for page in scraped:
            source_info = self.scorer.score_source(page["url"])
            evidence.append({**page, "source_info": source_info})
        
        evidence.sort(key=lambda x: x["source_info"]["score"], reverse=True)
        
        # Calculate source credibility
        avg_source_score = sum(e["source_info"]["score"] for e in evidence) / len(evidence) if evidence else 0
        
        # Analyze with Ollama
        analysis = self.analyze_evidence(claim, evidence)
        
        # Map verdict to status
        verdict_map = {
            "SUPPORTED": "verified",
            "CONTRADICTED": "false",
            "PARTIALLY_SUPPORTED": "partially_true",
        }
        status = verdict_map.get(analysis.get("verdict", ""), "unverifiable")
        
        # Final confidence
        llm_confidence = analysis.get("confidence", 50)
        final_confidence = int(llm_confidence * 0.7 + avg_source_score * 0.3)
        
        # Build source list
        sources = []
        for e in evidence[:5]:
            sources.append({
                "url": e["url"],
                "title": e["title"][:80] if e["title"] else e["source_info"]["domain"],
                "domain": e["source_info"]["domain"],
                "credibility": e["source_info"]["tier"],
                "score": e["source_info"]["score"]
            })
        
        return {
            "claim": claim,
            "status": status,
            "confidence_score": min(final_confidence, 100),
            "correction": analysis.get("correction"),
            "explanation": f"Based on {len(evidence)} sources",
            "key_facts": analysis.get("key_facts", []),
            "sources": sources,
            "sources_checked": len(evidence),
            "avg_source_credibility": round(avg_source_score, 1),
            "processing_time": round(time.time() - start_time, 2)
        }
    
    def verify_all_claims(self, claims: list) -> dict:
        """Verify all claims"""
        start_time = time.time()
        results = []
        
        summary = {
            "verified": 0,
            "false": 0,
            "partially_true": 0,
            "ambiguous": 0,
            "unverifiable": 0
        }
        
        total_sources = 0
        
        for i, claim in enumerate(claims):
            print(f"  Verifying claim {i+1}/{len(claims)}...")
            result = self.verify_single_claim(claim)
            results.append(result)
            status = result["status"]
            if status in summary:
                summary[status] += 1
            total_sources += result.get("sources_checked", 0)
        
        # Trust score
        total = len(claims)
        verifiable = total - summary["ambiguous"] - summary["unverifiable"]
        if verifiable > 0:
            trust = ((summary["verified"] + 0.5 * summary["partially_true"]) / verifiable) * 100
        else:
            trust = 0
        
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_claims": total,
            "summary": summary,
            "total_sources_checked": total_sources,
            "overall_trust_score": round(trust, 1),
            "processing_time": round(time.time() - start_time, 2),
            "results": results
        }


if __name__ == '__main__':
    verifier = ClaimVerifier()
    
    test_claims = [
        "Tesla was founded in 2003",
        "The Eiffel Tower is located in Berlin",
        "Python was created by Guido van Rossum",
    ]
    
    print("\n" + "="*60)
    print("WEB-BASED CLAIM VERIFICATION (Ollama)")
    print("="*60)
    
    for claim in test_claims:
        print(f"\n📋 Claim: {claim}")
        result = verifier.verify_single_claim(claim)
        print(f"   Status: {result['status'].upper()}")
        print(f"   Confidence: {result['confidence_score']}%")
        if result.get('correction'):
            print(f"   ❌ Correction: {result['correction']}")
        if result.get('key_facts'):
            print(f"   📚 Facts: {result['key_facts']}")
        print(f"   🔗 Sources: {result.get('sources_checked', 0)}")
        if result.get('sources'):
            for s in result['sources'][:2]:
                print(f"      - {s['domain']} ({s['credibility']})")
